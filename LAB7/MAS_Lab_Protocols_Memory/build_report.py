"""Build the submission PDF from the concise LAB7 report content."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"

ROWS = [
    ("1. Уточнение", "Условия задачи дополняются сохранёнными полями, а новые явные значения имеют приоритет; уточнение продолжает ту же A2A Task, а <i>search_rooms</i> вызывается как MCP-операция. Если строить требования только из очередной реплики, <i>{time: \"10:00\"}</i> потеряет дату и число участников и вместо предложения вызовет новое уточнение."),
    ("2. Перезапуск", "Checkpoint содержит владельца, task/context ID, требования, фазу, предложение и бронь; A2A Task не заменяет прикладной снимок. Если сохранить только требования, после перезапуска подтверждение не знает предложенную A-101. <b>Трасса:</b> taskId bfa6933e-aba8-4abf-a003-476fe79d0042; строки 13 (<i>agent.restart</i>) и 17 (<i>mcp.tool.call</i>)."),
    ("3. Новый диалог", "Профиль меняется только валидной инструкцией <i>remember</i>; сохраняются корпус, ID сообщения и ревизия. Новый Task читает профиль как долговременную память, а не восстанавливает старую переписку. Если запоминать корпус из любой заявки, разовый выбор B станет скрытой установкой профиля и исказит следующую независимую заявку."),
    ("4. Разовое исключение", "Явный корпус в текущем <i>patch</i> важнее профиля: память заполняет лишь отсутствующий корпус; без <i>remember</i> профиль не переписывается. Если всегда накладывать профиль после заявки, при памяти B и просьбе A будет предложен B; запись A в профиль также испортит будущие заявки, хотя следующая независимая задача вправе снова использовать B."),
    ("5. Перемешанные обращения", "Снимок адресуется однозначной парой (<i>user_id</i>, <i>task_id</i>), закодированной без коллизий; <i>contextId</i> не является ключом задачи. При ключе по пользователю или контексту две Task Alice в <i>shared-conversation</i> смешаются: заявка на A 6 ноября будет заменена заявкой на B 8 ноября; следовательно, одного <i>user_id</i> тоже недостаточно."),
    ("6. Устаревший вариант", "Только успешный <i>reserve_room</i> завершает Task; <i>occupied</i> очищает вариант, запускает поиск и требует нового подтверждения. Если завершать после любого ответа, отказ для A-101 выдаётся как бронь либо A-102 бронируется без согласия. <b>Трасса:</b> taskId c7bf0bc7-5924-474f-9042-673612149ae0; строки 12 (<i>occupied</i>) и 13 (новый поиск)."),
]


def main():
    pdfmetrics.registerFont(TTFont("DejaVu", FONT))
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleRu", parent=styles["Title"], fontName="DejaVu", fontSize=13,
                           leading=15, alignment=TA_CENTER, spaceAfter=4)
    body = ParagraphStyle("BodyRu", parent=styles["BodyText"], fontName="DejaVu", fontSize=7.4,
                          leading=9.1)
    label = ParagraphStyle("LabelRu", parent=body, fontName="DejaVu", fontSize=7.4,
                           leading=9.1)
    doc = SimpleDocTemplate(str(ROOT / "report.pdf"), pagesize=A4,
                            leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=11 * mm, bottomMargin=11 * mm)
    data = [[Paragraph("<b>Сценарий</b>", label), Paragraph("<b>Правило, альтернатива и контрпример</b>", label)]]
    data += [[Paragraph(f"<b>{name}</b>", label), Paragraph(text, body)] for name, text in ROWS]
    table = Table(data, colWidths=[36 * mm, 149 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("888888")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    conclusion = Paragraph("<b>Вывод.</b> A2A связывает сообщения с Task, MCP предоставляет ресурсы и операции над внешним состоянием. Корректность обеспечивают самостоятельные снимки, явное происхождение памяти и переходы автомата по фактическому ответу операции.", body)
    doc.build([Paragraph("Бюро бронирования: протоколы и память", title),
               Paragraph("Полный запуск: <b>6/6</b>.", body), Spacer(1, 3), table, Spacer(1, 4), conclusion])


if __name__ == "__main__":
    main()
