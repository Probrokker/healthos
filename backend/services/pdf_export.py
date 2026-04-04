"""
Экспорт медкарты в PDF.
Генерирует красивую выписку по профилю со всей историей.
"""
import io
import logging
import os
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


def generate_medical_card_pdf(profile, labs, visits, medications, growth_records, vaccines) -> bytes:
    """
    Генерирует PDF медкарты.
    Возвращает байты PDF-файла.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        raise ImportError("reportlab не установлен. Добавь в requirements.txt: reportlab==4.2.2")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title=f"Медкарта — {profile.name}"
    )

    # Стили
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=6,
    )
    style_subtitle = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#666666"),
        spaceAfter=12,
    )
    style_section = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#6366f1"),
        spaceBefore=16,
        spaceAfter=6,
        borderPad=4,
    )
    style_body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )
    style_small = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        leading=12,
    )

    # Цвета таблиц
    HEADER_BG = colors.HexColor("#6366f1")
    ROW_ALT = colors.HexColor("#f8f8ff")
    TABLE_BORDER = colors.HexColor("#e0e0e0")

    def make_table(headers, rows, col_widths=None):
        data = [headers] + rows
        t = Table(data, colWidths=col_widths)
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ])
        t.setStyle(style)
        return t

    today = date.today()
    age_years = today.year - profile.birthdate.year - (
        (today.month, today.day) < (profile.birthdate.month, profile.birthdate.day)
    )

    story = []

    # ── ЗАГОЛОВОК ──
    story.append(Paragraph(f"Медицинская карта", style_title))
    story.append(Paragraph(f"{profile.name}, {age_years} лет", style_subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#6366f1")))
    story.append(Spacer(1, 8))

    # Дата выгрузки
    story.append(Paragraph(
        f"Выгружено: {today.strftime('%d.%m.%Y')}  |  Health-OS",
        ParagraphStyle("Meta", parent=style_small, alignment=TA_RIGHT)
    ))
    story.append(Spacer(1, 12))

    # ── ОСНОВНЫЕ ДАННЫЕ ──
    story.append(Paragraph("Основные данные", style_section))

    base_data = [
        ["Дата рождения", profile.birthdate.strftime("%d.%m.%Y")],
        ["Возраст", f"{age_years} лет"],
        ["Пол", {"male": "Мужской", "female": "Женский"}.get(profile.gender or "", "—")],
        ["Группа крови", profile.blood_type or "—"],
        ["Аллергии", ", ".join(profile.allergies) if profile.allergies else "Нет"],
        ["Хронические заболевания", ", ".join(profile.chronic_conditions) if profile.chronic_conditions else "Нет"],
    ]

    t = Table(base_data, colWidths=[6*cm, 11*cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
        ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, ROW_ALT]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    # ── ВИЗИТЫ К ВРАЧАМ ──
    if visits:
        story.append(Paragraph(f"Визиты к врачам ({len(visits)})", style_section))
        rows = []
        for v in sorted(visits, key=lambda x: x.date, reverse=True)[:30]:
            diagnosis = (v.diagnosis or "—")[:60] + ("..." if len(v.diagnosis or "") > 60 else "")
            rows.append([
                v.date.strftime("%d.%m.%Y"),
                v.specialty or "—",
                v.doctor_name or "—",
                Paragraph(diagnosis, style_small),
            ])
        story.append(make_table(
            ["Дата", "Специальность", "Врач", "Диагноз"],
            rows,
            col_widths=[2.5*cm, 4*cm, 4.5*cm, 6*cm]
        ))

    # ── АКТИВНЫЕ ЛЕКАРСТВА ──
    active_meds = [m for m in medications if m.is_active]
    if active_meds:
        story.append(Paragraph(f"Текущие лекарства ({len(active_meds)})", style_section))
        rows = []
        for m in active_meds:
            end = m.end_date.strftime("%d.%m.%Y") if m.end_date else "бессрочно"
            rows.append([
                m.name,
                m.dosage or "—",
                m.frequency or "—",
                end,
                m.reason or "—",
            ])
        story.append(make_table(
            ["Препарат", "Доза", "Частота", "До", "Причина"],
            rows,
            col_widths=[4*cm, 2.5*cm, 3*cm, 2.5*cm, 5*cm]
        ))

    # ── АНАЛИЗЫ ──
    if labs:
        story.append(Paragraph(f"Лабораторные анализы ({len(labs)})", style_section))
        for lab in sorted(labs, key=lambda x: x.date, reverse=True)[:10]:
            story.append(Paragraph(
                f"<b>{lab.date.strftime('%d.%m.%Y')}</b> — {lab.test_type or 'Анализ'}"
                f"{' (' + lab.lab_name + ')' if lab.lab_name else ''}",
                style_body
            ))
            if lab.markers:
                abnormal = [m for m in lab.markers if m.get("status") not in ("normal", None)]
                normal_count = len(lab.markers) - len(abnormal)
                story.append(Paragraph(
                    f"Всего показателей: {len(lab.markers)}  |  В норме: {normal_count}"
                    f"{'  |  Вне нормы: ' + str(len(abnormal)) if abnormal else ''}",
                    style_small
                ))
                if abnormal:
                    rows = []
                    for m in abnormal:
                        direction = "↑" if m.get("status") in ("high", "critical_high") else "↓"
                        ref = f"{m.get('ref_min','?')}–{m.get('ref_max','?')}" if m.get("ref_min") else "—"
                        rows.append([
                            m.get("name", "—"),
                            f"{m.get('value','?')} {m.get('unit','')}",
                            direction,
                            ref
                        ])
                    story.append(make_table(
                        ["Показатель", "Значение", "", "Норма"],
                        rows,
                        col_widths=[7*cm, 3.5*cm, 1*cm, 5.5*cm]
                    ))
            story.append(Spacer(1, 6))

    # ── РОСТ И ВЕС ──
    if growth_records:
        story.append(Paragraph(f"Рост и вес ({len(growth_records)} измерений)", style_section))
        rows = []
        for g in sorted(growth_records, key=lambda x: x.date, reverse=True)[:10]:
            rows.append([
                g.date.strftime("%d.%m.%Y"),
                f"{g.height_cm} см" if g.height_cm else "—",
                f"{g.weight_kg} кг" if g.weight_kg else "—",
                str(g.bmi) if g.bmi else "—",
            ])
        story.append(make_table(
            ["Дата", "Рост", "Вес", "ИМТ"],
            rows,
            col_widths=[3.5*cm, 4*cm, 4*cm, 5.5*cm]
        ))

    # ── ПРИВИВКИ ──
    done_vaccines = [v for v in vaccines if v.is_completed]
    if done_vaccines:
        story.append(Paragraph(f"Прививки ({len(done_vaccines)})", style_section))
        rows = []
        for v in sorted(done_vaccines, key=lambda x: x.date_given or date.min, reverse=True):
            rows.append([
                v.date_given.strftime("%d.%m.%Y") if v.date_given else "—",
                v.name,
                v.clinic or "—",
            ])
        story.append(make_table(
            ["Дата", "Вакцина", "Клиника"],
            rows,
            col_widths=[3*cm, 10*cm, 4*cm]
        ))

    # ── ПОДВАЛ ──
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=TABLE_BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Документ сформирован системой Health-OS. Не является официальным медицинским документом.",
        ParagraphStyle("Footer", parent=style_small, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
