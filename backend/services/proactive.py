"""
Проактивные уведомления.
Запускается раз в день — проверяет все профили и отправляет напоминания.
"""
import asyncio
import logging
import os
from datetime import date, timedelta
from typing import Optional

from telegram import Bot
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")  # Telegram ID владельца


async def check_and_notify(db: Session):
    """Главная функция — проверяет всё и отправляет уведомления."""
    if not OWNER_CHAT_ID:
        logger.warning("OWNER_CHAT_ID не задан — уведомления отключены")
        return

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.database import Profile, DoctorVisit, LabResult, Vaccine, Medication
    from agents.vaccines_calendar import get_due_vaccines

    bot = Bot(token=TG_TOKEN)
    today = date.today()
    alerts = []

    profiles = db.query(Profile).all()

    for profile in profiles:
        name = profile.name

        # 1. Просроченные прививки (только дети)
        if profile.is_child:
            vaccines_raw = db.query(Vaccine).filter(
                Vaccine.profile_id == profile.id
            ).all()
            vaccines_list = [
                {"name": v.name, "date_given": v.date_given, "is_completed": v.is_completed}
                for v in vaccines_raw
            ]
            vaccine_data = get_due_vaccines(profile.birthdate, vaccines_list)

            if vaccine_data["overdue"]:
                for v in vaccine_data["overdue"][:2]:  # максимум 2 на профиль
                    alerts.append(
                        f"💉 {name} — просрочена прививка: {v['name']} "
                        f"(должна была быть в {v['was_due_at']})"
                    )

            if vaccine_data["upcoming"]:
                for v in vaccine_data["upcoming"][:1]:  # ближайшая
                    alerts.append(
                        f"📅 {name} — скоро прививка: {v['name']} (к {v['approx_date']})"
                    )

        # 2. Повторные визиты которые пора сделать
        visits = db.query(DoctorVisit).filter(
            DoctorVisit.profile_id == profile.id,
            DoctorVisit.follow_up_date.isnot(None)
        ).all()

        for visit in visits:
            if visit.follow_up_date:
                days_left = (visit.follow_up_date - today).days
                if 0 <= days_left <= 3:
                    alerts.append(
                        f"⏰ {name} — повторный визит к {visit.specialty or 'врачу'} "
                        f"{'сегодня' if days_left == 0 else f'через {days_left} дн.'}"
                    )
                elif days_left < 0 and days_left >= -7:
                    alerts.append(
                        f"⚠️ {name} — пропущен повторный визит к {visit.specialty or 'врачу'} "
                        f"({abs(days_left)} дн. назад)"
                    )

        # 3. Давно не сдавали анализы (взрослый — раз в полгода, дети — раз в год)
        last_lab = db.query(LabResult).filter(
            LabResult.profile_id == profile.id
        ).order_by(LabResult.date.desc()).first()

        if last_lab:
            days_since = (today - last_lab.date).days
            threshold = 180 if not profile.is_child else 365
            if days_since > threshold:
                alerts.append(
                    f"🔬 {name} — последние анализы {days_since} дней назад, "
                    f"пора обновить"
                )

        # 4. Заканчиваются лекарства
        active_meds = db.query(Medication).filter(
            Medication.profile_id == profile.id,
            Medication.is_active == True,
            Medication.end_date.isnot(None)
        ).all()

        for med in active_meds:
            if med.end_date:
                days_left = (med.end_date - today).days
                if 0 <= days_left <= 2:
                    alerts.append(
                        f"💊 {name} — {'завтра заканчивается' if days_left == 1 else 'сегодня последний день'} "
                        f"{med.name}"
                    )

    # Отправляем если есть что
    if alerts:
        text = "🏥 *Напоминания Health-OS*\n\n" + "\n".join(f"• {a}" for a in alerts)
        try:
            await bot.send_message(
                chat_id=int(OWNER_CHAT_ID),
                text=text,
                parse_mode="Markdown"
            )
            logger.info(f"Отправлено {len(alerts)} уведомлений")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомлений: {e}")
    else:
        logger.info("Нет активных уведомлений")


async def run_daily_check():
    """Точка входа для планировщика."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.database import SessionLocal

    db = SessionLocal()
    try:
        await check_and_notify(db)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_daily_check())
