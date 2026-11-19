from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Request:
    request_id: str
    message_id: str
    text: str

    @classmethod
    def from_json(cls, payload: object) -> Request:
        if not isinstance(payload, dict):
            raise ValueError("Ожидался JSON-объект.")
        fields = ("request_id", "message_id", "text")
        if any(not isinstance(payload.get(key), str) or not payload[key].strip() for key in fields):
            raise ValueError("request_id, message_id и text должны быть непустыми строками.")
        return cls(**{key: payload[key] for key in fields})


@dataclass(frozen=True)
class Response:
    status: str
    reply: str
    items: list[str] = field(default_factory=list)
    reservation_id: str | None = None

    def to_json(self) -> dict:
        return asdict(self)

