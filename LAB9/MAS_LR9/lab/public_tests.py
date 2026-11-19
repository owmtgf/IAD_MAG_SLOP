"""Обычные сценарии и сценарии восстановления для самопроверки."""
from __future__ import annotations

import argparse
from contextlib import closing, contextmanager
import json
import math
from pathlib import Path
from queue import Empty, Queue
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread

from .simulator import CRASH_EXIT_CODE, EquipmentSimulator, EquipmentUnavailable, TemporaryError


PROJECTOR = ("P-HDMI",)
USB_C_KIT = ("P-HDMI", "A-USBC-HDMI")
HDMI = "Нужен проектор для ноутбука с HDMI."
USB_C = "Нужен комплект для ноутбука с USB-C и DisplayPort Alt Mode. HDMI на ноутбуке нет."
CONFIRM = "Да, подтверждаю бронирование предложенного комплекта."
CHANGE = "Изменение: HDMI на ноутбуке нет. Есть только USB-C с DisplayPort Alt Mode."


class CheckFailed(RuntimeError):
    pass


class CriticalFailure(CheckFailed):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


class Session:
    def __init__(self, command: list[str], timeout: float, log_path: Path) -> None:
        self.timeout = timeout
        self.output: Queue[str | CheckFailed | None] = Queue()
        with log_path.open("a", encoding="utf-8") as log:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=log,
                encoding="utf-8",
                text=True,
                bufsize=1,
            )
        self.thread = Thread(target=self._read_output, daemon=True)
        self.thread.start()

    def _read_output(self) -> None:
        try:
            for line in self.process.stdout:
                self.output.put(line)
        except UnicodeError:
            self.output.put(CheckFailed("Ответ MAS в stdout должен быть закодирован в UTF-8."))
        finally:
            self.output.put(None)

    def send(self, message: dict) -> str | None:
        try:
            self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            raise CheckFailed("Процесс MAS завершился до получения сообщения.") from error
        try:
            answer = self.output.get(timeout=self.timeout)
        except Empty as error:
            raise CheckFailed(f"MAS не ответила за {self.timeout:g} с.") from error
        if isinstance(answer, CheckFailed):
            raise answer
        return answer

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=5)
        self.thread.join(timeout=5)
        for stream in (self.process.stdin, self.process.stdout):
            if not stream.closed:
                stream.close()

    def has_unread_output(self) -> bool:
        while not self.output.empty():
            if self.output.get_nowait() is not None:
                return True
        return False


class Scenario:
    def __init__(self, directory: Path, timeout: float) -> None:
        self.directory = directory
        self.timeout = timeout
        self.tools = EquipmentSimulator(directory)
        self.turns: list[dict] = []

    @contextmanager
    def start(self):
        command = [sys.executable, "-m", "lab.cli", "--state-dir", str(self.directory)]
        session = Session(command, self.timeout, self.directory / "stderr.log")
        try:
            yield session
        finally:
            session.stop()
        require(not session.has_unread_output(), "MAS вывела лишние строки в stdout.")

    def reservations(self) -> dict:
        with closing(sqlite3.connect(self.directory / "simulator.sqlite3")) as db, db:
            rows = db.execute("SELECT id, request_id, items FROM reservations").fetchall()
        return {request_id: (reservation_id, sorted(json.loads(items))) for reservation_id, request_id, items in rows}

    def arm_fault(self, name: str) -> None:
        with closing(sqlite3.connect(self.directory / "simulator.sqlite3")) as db, db:
            db.execute("INSERT INTO faults (name) VALUES (?)", (name,))

    def fault_progress(self, name: str) -> int:
        with closing(sqlite3.connect(self.directory / "simulator.sqlite3")) as db, db:
            row = db.execute("SELECT fired FROM faults WHERE name = ?", (name,)).fetchone()
        return row[0] if row else 0

    @staticmethod
    def check_reservation_changes(before: dict, after: dict, permitted_request: str | None) -> None:
        changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
        allowed = {permitted_request} if permitted_request is not None else set()
        if changed - allowed:
            raise CriticalFailure("В этом ходе обнаружено недопустимое изменение бронирований.")

    def step(
        self,
        session: Session,
        sequence: int,
        text: str,
        status: str,
        expected_items: tuple[str, ...] = (),
        *,
        may_book: bool = False,
        request_id: str = "public-case",
    ) -> None:
        before = self.reservations()
        message = {"request_id": request_id, "message_id": str(sequence), "text": text}
        entry = {"request": message, "expected_status": status, "expected_items": list(expected_items)}
        self.turns.append(entry)
        permitted_request = request_id if may_book else None
        try:
            raw = session.send(message)
        except CheckFailed as error:
            session.stop()
            after = self.reservations()
            entry.update(error=str(error), reservations=after)
            self.check_reservation_changes(before, after, permitted_request)
            raise
        after = self.reservations()
        entry.update(raw_response=raw, reservations=after)
        self.check_reservation_changes(before, after, permitted_request)
        require(raw is not None, "MAS завершилась без ответа. Проверьте stderr.")
        try:
            reply = json.loads(raw)
        except ValueError as error:
            raise CheckFailed("В stdout ожидается ровно один JSON-ответ на запрос.") from error
        require(isinstance(reply, dict), "Ответ должен быть JSON-объектом.")
        entry["response"] = reply
        entry.pop("raw_response", None)
        result = reply.get("status")
        items = reply.get("items")
        valid_items = isinstance(items, list) and all(isinstance(item, str) for item in items)
        reservation_id = reply.get("reservation_id")
        if result == "reserved":
            record = after.get(request_id)
            if record is None or reservation_id != record[0] or not valid_items or sorted(items) != record[1]:
                raise CriticalFailure("MAS сообщила об успешной брони без соответствующей записи в симуляторе.")
            if not may_book:
                raise CriticalFailure("Бронь заявлена в ответ на ход, который не подтверждает операцию.")
        require(result == status, f"Ожидался статус {status}, получено: {result}.")
        require(isinstance(reply.get("reply"), str) and bool(reply["reply"].strip()), "Нужен текст ответа.")
        require(valid_items, "Поле items должно быть списком строк.")
        require(sorted(items) == sorted(expected_items), f"Ожидался комплект {expected_items}, получено: {items}.")
        if status == "reserved":
            require(after[request_id][1] == sorted(expected_items), "В симуляторе записан другой комплект.")
        else:
            require(reservation_id is None, "Для этого статуса reservation_id должен быть null.")


def direct_hdmi(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, HDMI, "offer", PROJECTOR)


def adapter_needed(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, USB_C, "offer", USB_C_KIT)


def clarify_port(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, "Мне нужен проектор для ноутбука.", "clarify")
        case.step(session, 2, "На ноутбуке есть HDMI.", "offer", PROJECTOR)


def no_matching_items(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, "Нужен проектор, у ноутбука только mini DisplayPort.", "unavailable")


def change_request(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, HDMI, "offer", PROJECTOR)
        case.step(session, 2, CHANGE, "offer", USB_C_KIT)


def confirm_reservation(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, HDMI, "offer", PROJECTOR)
        case.step(session, 2, CONFIRM, "reserved", PROJECTOR, may_book=True)


def cancel_before_confirmation(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, HDMI, "offer", PROJECTOR)
        case.step(session, 2, "Отмените заявку, комплект больше не нужен.", "cancelled")


def stock_changed(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, HDMI, "offer", PROJECTOR)
        case.tools.reserve("other-request", list(PROJECTOR), idempotency_key="other-key")
        case.step(session, 2, CONFIRM, "unavailable")


def restart_before_confirmation(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, HDMI, "offer", PROJECTOR)
    with case.start() as session:
        case.step(session, 2, CONFIRM, "reserved", PROJECTOR, may_book=True)


def retry_catalog(case: Scenario) -> None:
    case.arm_fault("catalog_once")
    with case.start() as session:
        case.step(session, 1, HDMI, "offer", PROJECTOR)
    require(case.fault_progress("catalog_once") != 0, "Вызов каталога с временным сбоем не был выполнен.")
    require(case.fault_progress("catalog_once") == 2, "После временного сбоя каталог не был прочитан повторно.")


def restart_after_commit(case: Scenario) -> None:
    with case.start() as session:
        case.step(session, 1, HDMI, "offer", PROJECTOR)
        case.arm_fault("after_reserve")
        message = {"request_id": "public-case", "message_id": "2", "text": CONFIRM}
        raw = session.send(message)
        case.turns.append({
            "request": message, "expected": "process_exit_after_commit",
            "raw_response": raw, "reservations": case.reservations(),
        })
        require(raw is None, "После записи брони процесс должен прерваться до ответа.")
        require(session.process.wait(timeout=5) == CRASH_EXIT_CODE, "Процесс завершился с неожиданным кодом.")
    first = case.reservations()
    require(set(first) == {"public-case"}, "К моменту сбоя должна существовать ровно одна бронь.")
    with case.start() as session:
        case.step(session, 2, CONFIRM, "reserved", PROJECTOR, may_book=True)
    require(case.reservations() == first, "Повтор изменил первоначальную бронь.")


QUALITY = (
    ("HDMI напрямую", direct_hdmi),
    ("Комплект с переходником", adapter_needed),
    ("Уточнение", clarify_port),
    ("Несовместимое оборудование", no_matching_items),
    ("Изменение заявки", change_request),
    ("Подтверждение брони", confirm_reservation),
    ("Отмена до подтверждения", cancel_before_confirmation),
    ("Наличие изменилось", stock_changed),
)
RECOVERY = (
    ("Перезапуск до подтверждения", restart_before_confirmation),
    ("Повтор чтения каталога", retry_catalog),
    ("Перезапуск после записи брони", restart_after_commit),
)


def run_group(cases: tuple, root: Path, timeout: float, report: list[dict]) -> tuple[int, int, set[str]]:
    passed = critical = 0
    failures: set[str] = set()
    for index, (name, test) in enumerate(cases, start=1):
        directory = root / str(index)
        case = Scenario(directory, timeout)
        result = {"name": name, "turns": case.turns, "passed": False, "critical": False}
        report.append(result)
        try:
            test(case)
        except (CheckFailed, subprocess.TimeoutExpired) as error:
            if isinstance(error, CriticalFailure):
                critical += 1
                result["critical"] = True
            result["error"] = str(error)
            failures.add(name)
            print(f"НЕТ | {name} | {error}")
            log = directory / "stderr.log"
            if log.exists() and log.stat().st_size:
                print(log.read_text(encoding="utf-8", errors="replace")[-1200:].strip())
        else:
            passed += 1
            result["passed"] = True
            print(f" OK | {name}")
        log = directory / "stderr.log"
        events = []
        if log.is_file():
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("event") in (
                    "llm_call", "port_decision", "reply_choice",
                ):
                    events.append(event)
        result["model_events"] = events
    return passed, critical, failures


def simulator_only() -> None:
    with TemporaryDirectory(dir=Path.cwd(), prefix=".mas-lab-test-") as root:
        case = Scenario(Path(root), timeout=10)
        case.arm_fault("catalog_once")
        try:
            case.tools.list_catalog()
        except TemporaryError:
            pass
        else:
            raise CheckFailed("Симулятор не воспроизвёл временную ошибку.")
        require(len(case.tools.list_catalog()) == 3, "Проверка каталога не прошла.")
        first = case.tools.reserve("demo", list(PROJECTOR), idempotency_key="demo-key")
        second = case.tools.reserve("demo", list(PROJECTOR), idempotency_key="demo-key")
        require(first == second, "Повтор брони вернул другой результат.")
        restored = EquipmentSimulator(case.directory).get_reservation("demo")
        require(restored == first, "Симулятор не восстановил бронь.")
        try:
            case.tools.reserve("other", list(PROJECTOR), idempotency_key="other-key")
        except EquipmentUnavailable:
            pass
        else:
            raise CheckFailed("Симулятор выдал отсутствующую позицию.")
    print("Симулятор: каталог, временный сбой, бронь, повтор и восстановление — OK.")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=120, help="Максимум секунд на один ответ MAS.")
    parser.add_argument("--report", type=Path, help="Сохранить ответы и результаты открытых тестов в JSON.")
    parser.add_argument("--simulator-only", action="store_true", help="Проверить только стартовый симулятор.")
    args = parser.parse_args()
    if args.simulator_only:
        simulator_only()
        return
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout должен быть конечным числом больше нуля.")
    quality_cases: list[dict] = []
    recovery_cases: list[dict] = []
    with TemporaryDirectory(dir=Path.cwd(), prefix=".mas-lab-test-") as directory:
        root = Path(directory)
        quality, critical, failures = run_group(QUALITY, root / "quality", args.timeout, quality_cases)
        recovery, recovery_critical, _ = run_group(RECOVERY, root / "recovery", args.timeout, recovery_cases)
    confirmation_failed = "Подтверждение брони" in failures
    passed = quality >= 7 and not confirmation_failed and not critical and not recovery_critical and recovery == 3
    print(f"Качество: {quality}/8. Восстановление: {recovery}/3. Открытые автотесты: {'пройдены' if passed else 'не пройдены'}.")
    if args.report is not None:
        report = {
            "quality": {"passed": quality, "total": len(QUALITY), "cases": quality_cases},
            "recovery": {"passed": recovery, "total": len(RECOVERY), "cases": recovery_cases},
            "open_tests_passed": passed,
        }
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()

