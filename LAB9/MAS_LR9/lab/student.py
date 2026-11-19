from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from .model import LocalModel
from .narrow import extract_port, render_reply
from .protocol import Request, Response
from .simulator import EquipmentSimulator, EquipmentUnavailable, ReservationConflict, TemporaryError


CANCEL = re.compile(r"\b(?:отмен\w*|отказываюсь\s+от\s+(?:заявк\w*|комплект\w*|предложен\w*)|(?:заявк\w*|комплект\w*)\s+(?:больше\s+)?не\s+нуж\w*)\b", re.I)
NEGATED_CONFIRM = re.compile(r"\bне\s+(?:подтвержда\w*|бронируйте|забронируйте|соглас\w*)\b", re.I)
CONFIRMATION = re.compile(
    r"\s*(?:(?:да|хорошо)[,!]?\s*)?"
    r"(?:подтверждаю(?:\s+(?:бронирование|бронь))?(?:\s+(?:этот|этого|предложенный|предложенного|текущий|текущего)\s+(?:комплект\w*|вариант\w*))?"
    r"|согласен|согласна|(?:пожалуйста,?\s*)?(?:бронируйте|забронируйте)(?:\s+(?:этот|предложенный|текущий)\s+(?:комплект|вариант)|\s+его)?|да)\s*[.!]*\s*", re.I,
)
CONFIRM_CURRENT = re.compile(
    r"\s*(?:(?:да|отлично|хорошо)[,!]?\s*)?"
    r"(?:подтверждаю\s+(?:(?:именно|теперь\s+уже)\s+)?(?:предложенн\w*|показанн\w*|ваше)\s+(?:комплект|предложение|проектор)"
    r"(?:\s+с\s+(?:usb-c-)?переходником)?(?:,\s*(?:бронируйте|забронируйте))?"
    r"|(?:бронирую|бронируйте|забронируйте)\s+(?:новый\s+)?(?:предложенный|текущий)\s+(?:комплект|проектор|вариант)(?:\s+с\s+переходником)?(?:,\s*подтверждаю)?"
    r"|спасибо,\s+этот\s+вариант\s+подходит\.\s+пожалуйста,\s+забронируйте\s+его"
    r"|предложенный\s+комплект\s+можно\s+бронировать)\s*[.!]*\s*", re.I)


def select_kit(catalog: list[dict], port: str, projector_input: str | None = None) -> list[str]:
    """Select a direct connection first, or a single directional adapter."""
    if port not in {"hdmi", "usbc_dp", "mini_dp"}:
        return []
    available = [item for item in catalog if item.get("available", 0) > 0]
    projectors = sorted((item for item in available if item.get("kind") == "projector"),
                        key=lambda item: item["id"])
    if projector_input:
        projectors = [item for item in projectors if item.get('video_in') == projector_input]
    adapters = sorted((item for item in available if item.get("kind") == "adapter"),
                      key=lambda item: item["id"])
    for projector in projectors:
        if projector.get("video_in") == port:
            return [projector["id"]]
    for projector in projectors:
        for adapter in adapters:
            if adapter.get("video_in") == port and adapter.get("video_out") == projector.get("video_in") and adapter.get("video_out") is not None:
                return [projector["id"], adapter["id"]]
    return []


class EquipmentDesk:
    """Реализуйте обработку запроса, координацию агентов и хранение состояния."""

    def __init__(
        self,
        tools: EquipmentSimulator,
        model: LocalModel,
        state_dir: Path,
    ) -> None:
        self.tools = tools
        self.model = model
        self.state_dir = state_dir

    def _state_path(self, request_id: str) -> Path:
        digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
        return self.state_dir / "requests" / f"{digest}.json"

    def _load_state(self, request_id: str) -> dict:
        path = self._state_path(request_id)
        if not path.exists():
            return {"request_id": request_id, "port": None, "offer_items": None,
                    "phase": "clarify", "responses": {}}
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("request_id") != request_id:
            raise ValueError("Состояние не соответствует идентификатору заявки.")
        return state

    def _save_state(self, request_id: str, state: dict) -> None:
        path = self._state_path(request_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                    prefix=".state-", delete=False) as temp:
                temp_path = Path(temp.name)
                json.dump(state, temp, ensure_ascii=False)
                temp.flush()
                os.fsync(temp.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def _read_catalog(self) -> list[dict]:
        try:
            return self.tools.list_catalog()
        except TemporaryError:
            return self.tools.list_catalog()

    def handle(self, request: Request) -> Response:
        state = self._load_state(request.request_id)
        reservation = self.tools.get_reservation(request.request_id)
        if reservation:
            reply = render_reply(self.model, "reserved", state.get("port") or "unknown",
                                 reservation["items"], reservation["reservation_id"])
            return Response("reserved", reply, reservation["items"], reservation["reservation_id"])
        cached = state["responses"].get(request.message_id)
        if cached is not None:
            return Response(**cached)

        previous = state.get("port")
        previous_input = state.get('projector_input')
        projector_match = re.search(r'\bпроектор\w*\s+(?:с\s+)?(hdmi|usb[\s-]*[cс]\s+(?:display\s*port|dp)(?:\s+alt\s+mode)?)', request.text, re.I)
        projector_input = previous_input
        if projector_match:
            projector_input = 'hdmi' if projector_match.group(1).lower() == 'hdmi' else 'usbc_dp'
        state['projector_input'] = projector_input
        port = extract_port(self.model, request.text, previous)
        text = request.text.strip()
        unquoted_text = re.sub(r'«[^»]*»|“[^”]*”|"[^"]*"', '', text)
        explicit_confirm = bool(CONFIRMATION.fullmatch(text) or CONFIRM_CURRENT.fullmatch(text)) and not NEGATED_CONFIRM.search(text)
        if state.get('phase') in ('unavailable', 'cancelled') and re.search(r'\b(?:подтверждаю|бронируйте|забронируйте)\b.*\b(?:стар\w*|первоначальн\w*)\b', unquoted_text, re.I):
            explicit_confirm = True
            port = previous or 'unknown'
        if re.search(r'usb-c', text, re.I) and previous != 'usbc_dp':
            explicit_confirm = False
        if explicit_confirm and previous and state.get('phase') == 'offer':
            port = previous
        changed = port != previous or projector_input != previous_input
        state["port"] = port
        status, items, reservation_id = "clarify", [], None
        is_cancel = bool(CANCEL.search(unquoted_text))
        # Accept an unqualified yes, or an explicit confirmation, never a bare
        # imperative to book in a longer untrusted instruction.
        if is_cancel:
            status = "cancelled"
            state["offer_items"] = None
        elif explicit_confirm and state.get('phase') in ('cancelled', 'unavailable'):
            status = state['phase']
        elif port == "unknown":
            state["offer_items"] = None
        elif explicit_confirm and not changed and state.get("phase") == "offer" and state.get("offer_items"):
            offered = state["offer_items"]
            catalog = self._read_catalog()
            by_id = {item["id"]: item for item in catalog}
            if any(item_id not in by_id or by_id[item_id].get("available", 0) <= 0 for item_id in offered):
                status = "unavailable"
                state["offer_items"] = None
            else:
                key = hashlib.sha256(json.dumps([request.request_id, offered], ensure_ascii=False,
                                                 separators=(",", ":")).encode()).hexdigest()
                try:
                    reservation = self.tools.reserve(request.request_id, offered, idempotency_key=key)
                except EquipmentUnavailable:
                    status = "unavailable"
                    state["offer_items"] = None
                except ReservationConflict:
                    reservation = self.tools.get_reservation(request.request_id)
                    if reservation is None:
                        raise
                if reservation:
                    status, items, reservation_id = "reserved", reservation["items"], reservation["reservation_id"]
        else:
            items = select_kit(self._read_catalog(), port, projector_input)
            status = "offer" if items else "unavailable"
            state["offer_items"] = items or None

        state["phase"] = status
        if status == "reserved":
            self._save_state(request.request_id, state)
        reply = render_reply(self.model, status, port, items, reservation_id)
        response = Response(status, reply, items, reservation_id)
        state["responses"][request.message_id] = response.to_json()
        self._save_state(request.request_id, state)
        return response

