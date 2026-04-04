"""
Семейная аптечка.
Учёт что есть дома, срок годности, для кого предназначено.
"""
import json
import logging
import os
from datetime import date, timedelta
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))


def parse_chest_action(text: str) -> dict:
    """
    Claude парсит действие с аптечкой.
    Примеры:
    - «купил нурофен 200мг 10 таблеток»
    - «закончился парацетамол»
    - «что есть от температуры для детей?»
    - «что взять с собой в поездку с детьми?»
    """
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Определи действие с домашней аптечкой.

Текст: "{text}"

Верни ТОЛЬКО JSON:
{{
  "action": "add|remove|query|travel_pack",
  "item": {{
    "name": "название препарата",
    "form": "таблетки|сироп|капли|мазь|спрей|другое",
    "dosage": "дозировка или null",
    "quantity": "количество или null",
    "expiry_date": "YYYY-MM-DD или null",
    "for_whom": ["дети", "взрослые"] или конкретные имена,
    "location": "где хранится или null"
  }},
  "query_text": "что ищет пользователь если action=query",
  "travel_destination": "куда едут если action=travel_pack"
}}

action:
- add = добавить/купил/пополнил
- remove = закончился/использовал/выбросил
- query = что есть/найди/есть ли
- travel_pack = что взять в дорогу/в поездку"""
        }]
    )

    raw = response.content[0].text
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"action": "query", "item": {}, "query_text": text}


def format_chest_list(items: list, filter_text: str = "") -> str:
    """Форматирует список аптечки для Telegram."""
    if not items:
        if filter_text:
            return f"🔍 По запросу «{filter_text}» в аптечке ничего не найдено."
        return "🧴 Аптечка пуста. Напиши «купил [название]» чтобы добавить."

    today = date.today()
    lines = [f"🧴 *Домашняя аптечка*{' — ' + filter_text if filter_text else ''}\n"]

    expired = []
    expiring_soon = []
    ok = []

    for item in items:
        if item.expiry_date:
            days_left = (item.expiry_date - today).days
            if days_left < 0:
                expired.append(item)
            elif days_left <= 30:
                expiring_soon.append(item)
            else:
                ok.append(item)
        else:
            ok.append(item)

    if expired:
        lines.append("🔴 *Просрочено:*")
        for item in expired:
            lines.append(f"  • {item.name} {item.dosage or ''} — истёк {item.expiry_date.strftime('%d.%m.%Y')}")
        lines.append("")

    if expiring_soon:
        lines.append("🟡 *Скоро истекает:*")
        for item in expiring_soon:
            days = (item.expiry_date - today).days
            lines.append(f"  • {item.name} {item.dosage or ''} — через {days} дн. ({item.expiry_date.strftime('%d.%m.%Y')})")
        lines.append("")

    if ok:
        lines.append("✅ *В порядке:*")
        for item in ok:
            qty = f" ({item.quantity})" if item.quantity else ""
            exp = f" до {item.expiry_date.strftime('%d.%m.%Y')}" if item.expiry_date else ""
            whom = f" [{', '.join(item.for_whom)}]" if item.for_whom else ""
            lines.append(f"  • {item.name} {item.dosage or ''}{qty}{exp}{whom}")

    return "\n".join(lines)


def generate_travel_pack(items: list, has_children: bool, children_ages: list) -> str:
    """Генерирует список для поездки на основе аптечки и состава семьи."""
    available = [f"• {i.name} {i.dosage or ''}" for i in items if i.is_available]
    available_text = "\n".join(available) if available else "аптечка пуста"

    ages_text = ", ".join(f"{a} лет" for a in children_ages) if children_ages else ""
    family_text = f"Семья с детьми ({ages_text})" if has_children else "Взрослые"

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""Составь список лекарств для поездки.

Состав группы: {family_text}
Что есть в домашней аптечке:
{available_text}

Составь на русском:
1. **Взять из домашней аптечки** (только то что реально есть выше)
2. **Докупить** (чего не хватает для базового набора)

Базовый набор для семьи с детьми: жаропонижающее, обезболивающее, антигистаминное, антисептик, пластырь, средство от расстройства желудка, капли в нос.

Будь конкретным, не более 15 пунктов суммарно."""
        }]
    )

    return f"🧳 *Список для поездки*\n\n{response.content[0].text}"
