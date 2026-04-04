"""
Напоминания о приёме лекарств.
Парсит фразы типа «напомни Луке амоксициллин в 8, 14 и 20»
и отправляет уведомления в нужное время.
"""
import json
import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import anthropic

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")


def parse_reminder_request(text: str, profile_name: str) -> Optional[dict]:
    """
    Claude парсит запрос на напоминание.
    Возвращает структурированные данные или None если не распознал.
    """
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": f"""Из текста извлеки данные для напоминания о лекарстве.
Пациент: {profile_name}

Текст: "{text}"

Верни ТОЛЬКО JSON:
{{
  "medication_name": "название лекарства",
  "dosage": "дозировка или null",
  "times": ["08:00", "14:00", "20:00"],
  "duration_days": число или null,
  "start_today": true
}}

Правила:
- times в формате HH:MM (24ч)
- "утром" = 08:00, "днём" = 13:00, "вечером" = 19:00, "на ночь" = 21:00
- "3 раза в день" без указания времени = ["08:00", "14:00", "20:00"]
- "2 раза в день" = ["08:00", "20:00"]
- Если не удалось распознать лекарство — верни null вместо JSON"""
        }]
    )

    raw = response.content[0].text.strip()
    if raw.lower() == "null" or not raw:
        return None

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        pass
    return None


def format_reminder_confirmation(reminder_data: dict, profile_name: str, end_date: Optional[date]) -> str:
    """Форматирует подтверждение для пользователя."""
    times_str = ", ".join(reminder_data.get("times", []))
    duration = ""
    if end_date:
        days = (end_date - date.today()).days
        duration = f" ({days} дн., до {end_date.strftime('%d.%m')})"

    return (
        f"⏰ Напоминание создано для {profile_name}!\n\n"
        f"💊 {reminder_data.get('medication_name', '')}"
        f"{' ' + reminder_data['dosage'] if reminder_data.get('dosage') else ''}\n"
        f"🕐 Время: {times_str}{duration}\n\n"
        f"Буду напоминать каждый день в указанное время."
    )


async def send_medication_reminders(bot, db):
    """
    Проверяет активные напоминания и отправляет те что совпадают с текущим временем.
    Запускается каждую минуту.
    """
    from models.database import MedicationReminder, Profile

    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    today = date.today()

    reminders = db.query(MedicationReminder).filter(
        MedicationReminder.is_active == True
    ).all()

    for reminder in reminders:
        # Проверяем срок действия
        if reminder.end_date and today > reminder.end_date:
            reminder.is_active = False
            db.commit()
            continue

        if reminder.start_date and today < reminder.start_date:
            continue

        # Проверяем совпадение времени (±1 минута)
        times = reminder.times or []
        for t in times:
            try:
                reminder_time = datetime.strptime(t, "%H:%M")
                diff = abs(
                    now.hour * 60 + now.minute -
                    reminder_time.hour * 60 - reminder_time.minute
                )
                if diff <= 1:
                    profile = db.query(Profile).filter(
                        Profile.id == reminder.profile_id
                    ).first()
                    name = profile.name if profile else "?"

                    chat_id = reminder.chat_id or OWNER_CHAT_ID
                    if chat_id:
                        text = (
                            f"⏰ *Время принять лекарство!*\n\n"
                            f"👤 {name}\n"
                            f"💊 {reminder.medication_name}"
                            f"{' ' + reminder.dosage if reminder.dosage else ''}\n"
                            f"🕐 {t}"
                        )
                        try:
                            await bot.send_message(
                                chat_id=int(chat_id),
                                text=text,
                                parse_mode="Markdown"
                            )
                            logger.info(f"Напоминание отправлено: {name} — {reminder.medication_name} в {t}")
                        except Exception as e:
                            logger.error(f"Ошибка отправки напоминания: {e}")
                    break
            except ValueError:
                continue


async def check_expiring_reminders(bot, db):
    """Уведомляет когда курс лекарства заканчивается завтра."""
    from models.database import MedicationReminder, Profile

    tomorrow = date.today() + timedelta(days=1)

    reminders = db.query(MedicationReminder).filter(
        MedicationReminder.is_active == True,
        MedicationReminder.end_date == tomorrow
    ).all()

    for reminder in reminders:
        profile = db.query(Profile).filter(Profile.id == reminder.profile_id).first()
        name = profile.name if profile else "?"
        chat_id = reminder.chat_id or OWNER_CHAT_ID

        if chat_id:
            text = (
                f"📅 Завтра последний день!\n\n"
                f"💊 {name} — {reminder.medication_name}\n"
                f"Курс заканчивается {tomorrow.strftime('%d.%m.%Y')}"
            )
            try:
                await bot.send_message(chat_id=int(chat_id), text=text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Ошибка уведомления об окончании: {e}")
