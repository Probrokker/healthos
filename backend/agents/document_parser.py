"""
Распознавание медицинских документов:
- Рецепты от врача
- Выписные эпикризы
- Справки
- Направления
Claude Vision определяет тип документа и структурирует данные.
"""
import base64
import json
import os

import anthropic

client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

DOCUMENT_PARSE_PROMPT = """Ты — медицинский делопроизводитель. Определи тип документа и извлеки всю важную информацию.

Верни ТОЛЬКО JSON без объяснений:
{
  "document_type": "recipe|epicrisis|referral|certificate|analysis|other",
  "document_type_ru": "Рецепт|Выписной эпикриз|Направление|Справка|Анализ|Другой документ",
  "date": "YYYY-MM-DD или null",
  "doctor_name": "имя врача или null",
  "doctor_specialty": "специальность или null",
  "clinic": "название клиники или null",
  "patient_name": "имя пациента если видно или null",
  "diagnosis": "диагноз или null",
  "icd_code": "код МКБ если есть или null",
  "medications": [
    {
      "name": "название",
      "dosage": "дозировка",
      "frequency": "частота приёма",
      "duration": "длительность",
      "route": "способ приёма (внутрь/ингаляция/капли и т.д.)"
    }
  ],
  "procedures": ["список процедур если есть"],
  "recommendations": "рекомендации врача",
  "restrictions": "ограничения/противопоказания",
  "follow_up": "когда повторный визит",
  "referrals": ["направления к другим специалистам"],
  "validity_until": "срок действия документа YYYY-MM-DD или null",
  "key_findings": "ключевые выводы/заключение одним абзацем",
  "raw_notes": "всё что не вошло в структуру"
}

Правила:
- Дату формата ДД.ММ.ГГГГ конвертируй в YYYY-MM-DD
- Если документ на русском — все поля заполняй по-русски
- medications извлекай максимально подробно"""


def parse_document_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Распознаёт медицинский документ из изображения."""
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime_type, "data": image_b64}
                },
                {"type": "text", "text": DOCUMENT_PARSE_PROMPT}
            ]
        }]
    )

    return _extract_json(response.content[0].text)


def parse_document_from_text(text: str) -> dict:
    """Распознаёт медицинский документ из текста."""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": f"{DOCUMENT_PARSE_PROMPT}\n\nТЕКСТ ДОКУМЕНТА:\n{text}"
        }]
    )
    return _extract_json(response.content[0].text)


def _extract_json(text: str) -> dict:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return {
        "document_type": "other",
        "document_type_ru": "Документ",
        "date": None,
        "medications": [],
        "key_findings": text[:500],
        "parse_error": True
    }


def format_document_summary(parsed: dict, profile_name: str) -> str:
    """Форматирует краткий отчёт по документу для Telegram."""
    doc_icons = {
        "recipe": "📋",
        "epicrisis": "📄",
        "referral": "➡️",
        "certificate": "📜",
        "analysis": "🔬",
        "other": "📁"
    }
    icon = doc_icons.get(parsed.get("document_type", "other"), "📁")
    doc_type = parsed.get("document_type_ru", "Документ")

    lines = [
        f"{icon} *{doc_type}* — {profile_name}",
        f"📅 Дата: {parsed.get('date') or 'не указана'}",
    ]

    if parsed.get("doctor_name"):
        spec = f" ({parsed['doctor_specialty']})" if parsed.get("doctor_specialty") else ""
        lines.append(f"👨‍⚕️ Врач: {parsed['doctor_name']}{spec}")

    if parsed.get("clinic"):
        lines.append(f"🏥 Клиника: {parsed['clinic']}")

    if parsed.get("diagnosis"):
        icd = f" [{parsed['icd_code']}]" if parsed.get("icd_code") else ""
        lines.append(f"🩺 Диагноз: {parsed['diagnosis']}{icd}")

    if parsed.get("medications"):
        lines.append(f"\n💊 *Назначения ({len(parsed['medications'])}):**")
        for med in parsed["medications"]:
            parts = [f"• {med.get('name', '?')}"]
            if med.get("dosage"):
                parts.append(med["dosage"])
            if med.get("frequency"):
                parts.append(med["frequency"])
            if med.get("duration"):
                parts.append(f"— {med['duration']}")
            lines.append(" ".join(parts))

    if parsed.get("recommendations"):
        lines.append(f"\n📝 Рекомендации: {parsed['recommendations'][:300]}")

    if parsed.get("follow_up"):
        lines.append(f"🔄 Повторный визит: {parsed['follow_up']}")

    if parsed.get("referrals"):
        lines.append(f"➡️ Направления: {', '.join(parsed['referrals'])}")

    if parsed.get("restrictions"):
        lines.append(f"⚠️ Ограничения: {parsed['restrictions'][:200]}")

    if parsed.get("validity_until"):
        lines.append(f"⏰ Действителен до: {parsed['validity_until']}")

    return "\n".join(lines)


def get_actions_from_document(parsed: dict) -> dict:
    """Определяет что нужно сохранить в БД из документа."""
    actions = {
        "save_visit": False,
        "save_medications": [],
        "visit_data": {},
    }

    # Если есть диагноз или врач — сохраняем как визит
    if parsed.get("diagnosis") or parsed.get("doctor_name"):
        actions["save_visit"] = True
        actions["visit_data"] = {
            "specialty": parsed.get("doctor_specialty", ""),
            "doctor_name": parsed.get("doctor_name", ""),
            "diagnosis": parsed.get("diagnosis", ""),
            "recommendations": parsed.get("recommendations", ""),
            "follow_up": parsed.get("follow_up"),
        }

    # Если есть назначения — сохраняем как лекарства
    for med in parsed.get("medications", []):
        if med.get("name"):
            actions["save_medications"].append({
                "name": med["name"],
                "dosage": med.get("dosage"),
                "frequency": med.get("frequency"),
                "duration": med.get("duration"),
                "reason": parsed.get("diagnosis", ""),
            })

    return actions
