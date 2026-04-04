"""
Парсинг анализов из фото/PDF через Claude Vision.
Возвращает структурированный JSON с маркерами.
"""
import anthropic
import base64
import os
import re
from pathlib import Path
from typing import Optional
import json

client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

LAB_PARSE_PROMPT = """Ты — медицинский лаборант-аналитик. Твоя задача — извлечь все лабораторные показатели из изображения или текста анализа.

Верни ТОЛЬКО JSON (без объяснений) в формате:
{
  "lab_name": "название лаборатории или клиники",
  "date": "YYYY-MM-DD или null если не видно",
  "test_type": "тип анализа (ОАК, биохимия, гормоны и т.д.)",
  "patient_name": "имя пациента если видно",
  "markers": [
    {
      "name": "название показателя на русском",
      "name_en": "английское название если есть",
      "value": "числовое значение как строка",
      "unit": "единица измерения",
      "ref_min": "нижняя граница нормы или null",
      "ref_max": "верхняя граница нормы или null",
      "status": "normal|low|high|critical_low|critical_high"
    }
  ],
  "raw_notes": "любые примечания врача лаборатории"
}

Правила:
- Извлеки ВСЕ показатели, даже если они в норме
- Если референс не указан — поставь null
- status определяй по референсным значениям на бланке
- Если показатель вне нормы — обязательно укажи это в status
- Дату формата ДД.ММ.ГГГГ конвертируй в YYYY-MM-DD"""


def parse_lab_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Парсит анализ из изображения через Claude Vision."""
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": LAB_PARSE_PROMPT
                    }
                ],
            }
        ],
    )

    text = response.content[0].text
    return _extract_json(text)


def parse_lab_from_text(text: str) -> dict:
    """Парсит анализ из текста (например PDF → text)."""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": f"{LAB_PARSE_PROMPT}\n\nТЕКСТ АНАЛИЗА:\n{text}"
            }
        ],
    )

    return _extract_json(response.content[0].text)


def _extract_json(text: str) -> dict:
    """Надёжно извлекает JSON из ответа модели."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != 0:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass

    return {
        "lab_name": "не определено",
        "date": None,
        "test_type": "не определено",
        "patient_name": None,
        "markers": [],
        "raw_notes": text,
        "parse_error": True
    }


def format_lab_summary(parsed: dict, profile_name: str) -> str:
    """Формирует краткий текстовый отчёт по анализу для Telegram."""
    markers = parsed.get("markers", [])
    if not markers:
        return "❌ Не удалось извлечь показатели из анализа."

    abnormal = [m for m in markers if m.get("status") not in ("normal", None)]
    normal_count = len(markers) - len(abnormal)

    lines = [
        f"🔬 **{parsed.get('test_type', 'Анализ')}** — {profile_name}",
        f"📅 Дата: {parsed.get('date', 'не указана')}",
        f"🏥 Лаборатория: {parsed.get('lab_name', 'не указана')}",
        f"",
        f"✅ В норме: {normal_count} показателей",
    ]

    if abnormal:
        lines.append(f"⚠️ Вне нормы: {len(abnormal)}")
        lines.append("")
        for m in abnormal:
            status_icon = "🔴" if "critical" in m.get("status", "") else "🟡"
            direction = "↑" if m.get("status") in ("high", "critical_high") else "↓"
            ref = ""
            if m.get("ref_min") and m.get("ref_max"):
                ref = f" (норма: {m['ref_min']}–{m['ref_max']} {m.get('unit', '')})"
            elif m.get("ref_min"):
                ref = f" (норма: >{m['ref_min']} {m.get('unit', '')})"
            elif m.get("ref_max"):
                ref = f" (норма: <{m['ref_max']} {m.get('unit', '')})"
            lines.append(f"{status_icon} {m['name']}: {m['value']} {m.get('unit', '')} {direction}{ref}")
    else:
        lines.append("🎉 Все показатели в норме!")

    return "\n".join(lines)


def get_mime_type(filename: str) -> str:
    """Определяет MIME-тип по расширению файла."""
    ext = Path(filename).suffix.lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }
    return mapping.get(ext, "image/jpeg")
