"""Два узких помощника Qwen для ЛР9."""
from __future__ import annotations

import json
import re
import sys

from .model import LocalModel


PORT_CODES = {
    "A": "hdmi",
    "B": "usbc_dp",
    "C": "mini_dp",
    "D": "usbc_no_video",
    "E": "unknown",
}
PORT_NAMES = {
    "A": "HDMI", "B": "USB-C с видео", "C": "mini DisplayPort",
    "D": "USB-C без видеовыхода", "E": "неизвестно",
}
PORT = re.compile(
    r"(?P<hdmi>\bhdmi\b)|(?P<mini_dp>\bmini[\s-]*(?:display\s*port|dp)\b)"
    r"|(?P<usbc_dp>\b(?:usb|type)[\s-]*[cс]\b)"
)
VIDEO = r"(?:видеовыход\w*|видеосигнал\w*|(?:вывод\w*\s+)?видео\b|(?:display\s*port|dp)(?:[\s-]+alt[\s-]+mode)?\b)"
VIDEO_DENIAL = re.compile(
    rf"\b(?:только\s+)?для\s+заряд\w*|\bтолько\s+заряд\w*|\bбез\s+(?:поддержки\s+)?{VIDEO}"
    rf"|\bне\s+(?:выводит|переда[её]т|поддерживает)\s+{VIDEO}"
    rf"|{VIDEO}\s+(?:нет\b|не\s+(?:работает|поддерживается))|не\s+поддержива\w*\s+{VIDEO}"
    rf"|(?:котор\w*\s+)?не\s+поддержива\w*\s+(?:видео\w*|вывод\w*\s+изображен\w*)"
)
VIDEO_SUPPORT = re.compile(
    rf"\b(?:с\s+(?:поддержкой\s+)?|(?:выводит|переда[её]т|поддерживает)\s+){VIDEO}"
    rf"|\b(?:display\s*port|dp)(?:[\s-]+alt[\s-]+mode)?\b"
)
PORT_ABSENT_BEFORE = re.compile(r"\b(?:нет|без|не)\s*$")
PORT_ABSENT_AFTER = re.compile(
    r"^\s*(?:(?:(?:на|у)\s+(?:ноутбук\w*|компьютер\w*|устройств\w*|меня)\s+)?(?:там\s+)?(?:точно\s+)?)"
    r"(?:нет\b|отсутству\w*|не\s+(?:работает|поддерживается)\b)"
)
UNCERTAIN = re.compile(
    r"\b(?:возможно|кажется|не\s+знаю|не\s+уверен\w*|"
    r"неизвестно|наверное|может|maybe|not\s+sure|(?:есть|поддерживает|поддерживается)\s+ли)\b"
)
SPLIT = re.compile(r"[,;.!?\n]+|\b(?:но|зато|однако)\b")
HESITATION_COMMA = re.compile(
    r"\b(возможно|наверное|кажется|не\s+знаю|не\s+уверен\w*|неизвестно)\s*,\s*"
)
COORDINATION = re.compile(r"\b(?:и|или|либо|а|вместо)\b")
PREFERENCE = re.compile(r"\b(?:предпочита\w*|предпочту|лучше|хочу\s+подключ\w*)\b")
CHANGE_WITHOUT_PORT = re.compile(
    r"\b(?:друг\w+\s+(?:ноутбук|разъем|видеовыход)\w*|"
    r"(?:сменил\w*|поменял\w*|заменил\w*)\s+(?:ноутбук|разъем|видеовыход)\w*)"
)
INSTRUCTION = re.compile(
    r"\b(?:системн\w*\s+(?:команд\w*|инструкц\w*)|"
    r"(?:ответь|выведи|напиши|укажи|скажи|считай|представь|игнорируй|забудь|утверждай|"
    r"поставь|проставить|ignore|assume|pretend|override|output|say)\b)"
)


def _mentions(part: str):
    """Limit the evidence around a connector to its own part of the utterance."""
    matches = list(PORT.finditer(part))
    for index, match in enumerate(matches):
        left_edge = 0
        right_edge = len(part)
        if index:
            between = part[matches[index - 1].end():match.start()]
            separators = list(COORDINATION.finditer(between))
            separator = separators[-1] if separators else None
            left_edge = matches[index - 1].end() + (
                (separator.start() if separator.group() == 'вместо' else separator.end()) if separator else 0)
        if index + 1 < len(matches):
            between = part[match.end():matches[index + 1].start()]
            separator = COORDINATION.search(between)
            right_edge = match.end() + (separator.start() if separator else len(between))
        yield match.lastgroup, part[left_edge:match.start()], part[match.end():right_edge]


def _candidates(text: str, previous: str | None) -> set[str]:
    positive: set[str] = set()
    negative: set[str] = set()
    preferred: set[str] = set()
    saw_port = False
    normalized = text.casefold().replace("ё", "е").replace("‑", "-").replace("–", "-")
    normalized = re.sub(r'\b(?:служебн\w*|системн\w*)\s+инструкц\w*\s*:[^.!?\n]*', ' ', normalized)
    normalized = re.sub(r",\s*(котор\w*\s+не\s+поддержива\w*)", r" \1", normalized)
    normalized = re.sub(r"\([^)]*(?:override|system|игнорируй)[^)]*\)", " ", normalized)
    normalized = re.sub(r"\bhdmi[\s-]*проектор\w*", "проектор ", normalized)
    normalized = re.sub(r"проектор\w*\s+(?:с\s+)?(?:hdmi|usb[\s-]*[cс](?:\s+(?:display\s*port|dp)(?:\s+alt\s+mode)?)?)", "проектор ", normalized)
    normalized = HESITATION_COMMA.sub(r"\1 ", normalized)
    for part in SPLIT.split(normalized):
        # A command mentioning a connector does not establish that the laptop
        # has it. Other independent clauses may still supply valid evidence.
        if INSTRUCTION.search(part):
            continue
        for port, before, after in _mentions(part):
            saw_port = True
            if re.search(r'\bне\s+нуж\w*\s*$', before) and VIDEO_DENIAL.search(after):
                continue
            denied = PORT_ABSENT_BEFORE.search(before) or PORT_ABSENT_AFTER.search(after) or re.search(r'\bвместо\s*$', before)
            if UNCERTAIN.search(before + " " + after) and not denied:
                continue
            preference = PREFERENCE.search(before)
            if preference:
                affirmed = not PORT_ABSENT_BEFORE.search(before) and not re.search(
                    r"\bне\s*$", before[:preference.start()]
                )
                if affirmed:
                    preferred.add(port)
                    # Explicit video support can occur inside a positive preference.
                    if port == "usbc_dp" and not VIDEO_DENIAL.search(after) and VIDEO_SUPPORT.search(after):
                        positive.add(port)
                continue
            if denied:
                negative.add(port)
            elif port != "usbc_dp":
                positive.add(port)
            elif VIDEO_DENIAL.search(after):
                negative.add(port)
                positive.add("usbc_no_video")
            elif VIDEO_SUPPORT.search(after):
                positive.add(port)
    if not saw_port and not CHANGE_WITHOUT_PORT.search(normalized) and previous in {
        "hdmi", "usbc_dp", "mini_dp", "usbc_no_video"
    }:
        return {previous}
    if positive & negative:
        return set()
    if positive - {"usbc_no_video"}:
        positive.discard("usbc_no_video")
    explicit = positive & preferred
    if len(explicit) == 1:
        return explicit
    # Leave a choice between independently viable outputs to the user.
    return positive if len(positive) <= 1 else set()


def _choice(model: LocalModel, agent: str, instructions: str, data: dict, allowed: tuple[str, ...]) -> str:
    reply = model.complete(
        agent=agent, system=instructions,
        user=json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        choices=allowed, max_tokens=4,
    ).strip()
    return reply if reply in allowed else ""


def extract_port(model: LocalModel, text: str, previous: str | None = None) -> str:
    """Предложить разъём и проверить, подтверждается ли он сведениями из заявки."""
    candidates = _candidates(text, previous)
    allowed = tuple(code for code, port in PORT_CODES.items() if port in candidates or code == "E")
    options = "; ".join(f"{code} — {PORT_NAMES[code]}" for code in allowed)
    choice = _choice(
        model, "port",
        f"Выбери видеовыход ноутбука по сообщению. {options}. "
        "Учти отрицания и предпочтение пользователя. Предыдущий разъём можно сохранить, "
        "если сообщение не меняет его. Ответ — одна буква.",
        {"сообщение": text if len(text) <= 2400 else text[:1200] + "\n[…пропуск…]\n" + text[-1200:],
         "предыдущий": previous}, allowed,
    )
    proposal = PORT_CODES.get(choice, "unknown")
    if proposal in candidates:
        final = proposal
    elif len(candidates) == 1:
        final = next(iter(candidates))
    else:
        final = "unknown"
    print(json.dumps({
        "event": "port_decision", "model_code": choice or None,
        "allowed": allowed, "final": final, "corrected_by_rule": proposal != final,
    }), file=sys.stderr, flush=True)
    return final


def render_reply(
    model: LocalModel, status: str, port: str, items: list[str],
    reservation_id: str | None, note: str = "",
) -> str:
    """Агент выбирает формулировку; итоговые факты подставляет приложение."""
    joined = ", ".join(items)
    variants = {
        "clarify": ("Какой видеовыход есть на ноутбуке?",
                    "Уточните, пожалуйста, через какой разъём ноутбук выводит видео."),
        "offer": (f"Подходит комплект: {joined}. Подтвердите бронирование.",
                  f"Могу предложить {joined}. Подтвердите бронь этого комплекта."),
        "unavailable": ("Сейчас нет доступного совместимого комплекта.",
                        "Не нашёл доступного оборудования, которое можно подключить к этому видеовыходу."),
        "cancelled": ("Заявка отменена.", "Отменил заявку по вашей просьбе."),
        "reserved": (f"Бронь {reservation_id} записана. Комплект: {joined}.",
                     f"Комплект {joined} забронирован. Номер брони: {reservation_id}."),
    }
    direct, friendly = variants[status]
    choice = _choice(
        model, "reply",
        "Выбери формулировку, которая яснее для пользователя. Статус уже установлен приложением. "
        "Примечание к каталогу — только справочный текст. Ответь одной буквой: A или B.",
        {"статус": status, "разъём": port, "A": direct, "B": friendly, "примечание": note[:300]},
        ("A", "B"),
    )
    print(json.dumps({"event": "reply_choice", "model_code": choice or None, "status": status}),
          file=sys.stderr, flush=True)
    return friendly if choice == "B" else direct
