from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4


CRASH_EXIT_CODE = 86


class TemporaryError(RuntimeError):
    """Временная ошибка инструмента. Вызов можно повторить."""


class EquipmentUnavailable(RuntimeError):
    """Хотя бы одной позиции комплекта нет в наличии."""


class ReservationConflict(RuntimeError):
    """Запрошенная бронь конфликтует с ранее сохранённой."""


class EquipmentSimulator:
    def __init__(self, state_dir: Path, catalog_path: Path | None = None) -> None:
        state_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = state_dir / "simulator.sqlite3"
        path = catalog_path or Path(__file__).with_name("catalog.json")
        self._catalog = {item["id"]: item for item in json.loads(path.read_text(encoding="utf-8"))}
        with self._connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS reservations (
                    id TEXT PRIMARY KEY,
                    request_id TEXT UNIQUE NOT NULL,
                    idem_key TEXT UNIQUE NOT NULL,
                    items TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS faults (
                    name TEXT PRIMARY KEY,
                    fired INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self._db_path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _consume_fault(self, db: sqlite3.Connection, name: str) -> bool:
        change = db.execute("UPDATE faults SET fired = 1 WHERE name = ? AND fired = 0", (name,))
        return change.rowcount == 1

    def _availability(self, db: sqlite3.Connection) -> dict[str, int]:
        stock = {item_id: item["quantity"] for item_id, item in self._catalog.items()}
        for row in db.execute("SELECT items FROM reservations"):
            for item_id in json.loads(row["items"]):
                if item_id in stock:
                    stock[item_id] -= 1
        return stock

    @staticmethod
    def _record(row: sqlite3.Row) -> dict:
        return {
            "reservation_id": row["id"],
            "request_id": row["request_id"],
            "items": json.loads(row["items"]),
        }

    def list_catalog(self) -> list[dict]:
        """Вернуть позиции с id, kind, note и текущим available."""
        with self._connection() as db:
            failed = self._consume_fault(db, "catalog_once")
            stock = {} if failed else self._availability(db)
            if not failed:
                db.execute("UPDATE faults SET fired = 2 WHERE name = 'catalog_once' AND fired = 1")
        if failed:
            raise TemporaryError("Каталог временно недоступен.")
        return [
            {
                "id": item_id,
                "kind": item["kind"],
                "video_in": item.get("video_in"),
                "video_out": item.get("video_out"),
                "note": item["note"],
                "available": stock[item_id],
            }
            for item_id, item in self._catalog.items()
        ]

    def get_reservation(self, request_id: str) -> dict | None:
        """Найти сохранённую бронь по идентификатору заявки."""
        with self._connection() as db:
            row = db.execute("SELECT * FROM reservations WHERE request_id = ?", (request_id,)).fetchone()
        return self._record(row) if row else None

    def reserve(self, request_id: str, items: list[str], *, idempotency_key: str) -> dict:
        """Атомарно записать бронь, повтор того же вызова вернёт прежний результат."""
        if not request_id or not idempotency_key:
            raise ValueError("Нужны идентификатор заявки и ключ идемпотентности.")
        if not items or len(items) != len(set(items)) or any(item not in self._catalog for item in items):
            raise ValueError("Комплект должен состоять из известных уникальных позиций.")
        item_ids = sorted(items)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT * FROM reservations WHERE idem_key = ?", (idempotency_key,)).fetchone()
            if prior:
                if prior["request_id"] != request_id or json.loads(prior["items"]) != item_ids:
                    raise ReservationConflict("Ключ уже связан с другой операцией.")
                return self._record(prior)
            prior_for_request = db.execute(
                "SELECT 1 FROM reservations WHERE request_id = ?", (request_id,)
            ).fetchone()
            if prior_for_request:
                raise ReservationConflict("Для заявки уже есть бронь.")
            stock = self._availability(db)
            if any(stock[item_id] <= 0 for item_id in item_ids):
                raise EquipmentUnavailable("Оборудование недоступно.")
            reservation_id = f"R-{uuid4().hex[:12]}"
            db.execute(
                "INSERT INTO reservations (id, request_id, idem_key, items) VALUES (?, ?, ?, ?)",
                (reservation_id, request_id, idempotency_key, json.dumps(item_ids)),
            )
            crash = self._consume_fault(db, "after_reserve")
        if crash:
            os._exit(CRASH_EXIT_CODE)
        return {"reservation_id": reservation_id, "request_id": request_id, "items": item_ids}

