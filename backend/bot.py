"""
Health-OS Telegram Bot — главный файл.
Обрабатывает все команды и сообщения.
"""
import asyncio
import io
import json
import logging
import os
import sys
from datetime import date, datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from sqlalchemy.orm import Session

# Добавляем пути
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "services"))

from models.database import SessionLocal, Profile, LabResult, DoctorVisit, Medication, GrowthRecord, Vaccine, create_tables
from agents.lab_parser import parse_lab_from_image, parse_lab_from_text, format_lab_summary, get_mime_type
from agents.base_agent import run_consilium, run_single_agent, calculate_age, get_specialist_list
from agents.who_percentiles import format_growth_report
from agents.vaccines_calendar import get_due_vaccines, format_vaccine_report
from services.context_builder import build_profile_context, get_labs_trend

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = set(map(int, os.getenv("ALLOWED_USER_IDS", "").split(",") if os.getenv("ALLOWED_USER_IDS") else []))


def get_db() -> Session:
    return SessionLocal()


def check_auth(user_id: int) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


def get_profile_by_name(db: Session, name: str) -> Optional[Profile]:
    """Ищет профиль по имени (частичное совпадение)."""
    name_lower = name.lower().strip()
    profiles = db.query(Profile).all()
    for p in profiles:
        if p.name.lower().startswith(name_lower) or name_lower in p.name.lower():
            return p
    return None


def get_profile_keyboard(db: Session) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора профиля."""
    profiles = db.query(Profile).all()
    buttons = []
    for i in range(0, len(profiles), 2):
        row = [InlineKeyboardButton(profiles[i].name, callback_data=f"profile_{profiles[i].id}")]
        if i + 1 < len(profiles):
            row.append(InlineKeyboardButton(profiles[i+1].name, callback_data=f"profile_{profiles[i+1].id}"))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# === HANDLERS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update.effective_user.id):
        return
    db = get_db()
    try:
        profiles = db.query(Profile).all()
        names = ", ".join(p.name for p in profiles)
        text = (
            "🏥 **Health-OS** — семейный медицинский ассистент\n\n"
            f"👨‍👩‍👧‍👦 Профили: {names}\n\n"
            "**Команды:**\n"
            "/кому — выбрать профиль\n"
            "/labs [имя] [показатель] — тренд анализа\n"
            "/визит [имя] — записать визит к врачу\n"
            "/лекарство [имя] — добавить лекарство\n"
            "/рост [имя] [рост] [вес] — записать рост/вес\n"
            "/прививки [имя] — статус вакцинации\n"
            "/консилиум [имя] [проблема] — полный анализ\n"
            "/врач [имя] [специальность] — подготовка к врачу\n"
            "/профиль [имя] — показать профиль\n"
            "/обновить [имя] — обновить данные профиля\n\n"
            "📸 Отправь **фото/PDF анализа** — я автоматически распознаю и сохраню"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        db.close()


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update.effective_user.id):
        return
    args = context.args
    db = get_db()
    try:
        if not args:
            await update.message.reply_text("Выберите профиль:", reply_markup=get_profile_keyboard(db))
            return

        name = " ".join(args)
        profile = get_profile_by_name(db, name)
        if not profile:
            await update.message.reply_text(f"Профиль '{name}' не найден.")
            return

        today = date.today()
        age_info = calculate_age(profile.birthdate)
        age_str = f"{age_info['years']} лет {age_info['months']} мес." if profile.is_child else f"{age_info['years']} лет"

        labs_count = db.query(LabResult).filter(LabResult.profile_id == profile.id).count()
        visits_count = db.query(DoctorVisit).filter(DoctorVisit.profile_id == profile.id).count()
        active_meds = db.query(Medication).filter(Medication.profile_id == profile.id, Medication.is_active == True).count()

        text = (
            f"👤 **{profile.name}**\n"
            f"🎂 ДР: {profile.birthdate.strftime('%d.%m.%Y')} ({age_str})\n"
            f"🩸 Группа крови: {profile.blood_type or 'не указана'}\n"
            f"⚠️ Аллергии: {', '.join(profile.allergies) if profile.allergies else 'нет'}\n"
            f"🏥 Хронические: {', '.join(profile.chronic_conditions) if profile.chronic_conditions else 'нет'}\n\n"
            f"📊 Анализов в БД: {labs_count}\n"
            f"👨‍⚕️ Визитов: {visits_count}\n"
            f"💊 Активных лекарств: {active_meds}\n"
        )
        if profile.notes:
            text += f"\n📝 {profile.notes}"

        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        db.close()


async def cmd_labs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /labs [имя] [показатель]\nПример: /labs София гемоглобин")
        return

    db = get_db()
    try:
        profile = get_profile_by_name(db, args[0])
        if not profile:
            await update.message.reply_text(f"Профиль '{args[0]}' не найден.")
            return

        if len(args) > 1:
            marker_name = " ".join(args[1:])
            trend = get_labs_trend(db, profile.id, marker_name)
            if not trend:
                await update.message.reply_text(f"Данных по '{marker_name}' для {profile.name} нет.")
                return

            lines = [f"📈 **{marker_name} — {profile.name}**\n"]
            for point in trend:
                status_icon = "✅" if point["status"] == "normal" else ("🔴" if "critical" in point["status"] else "🟡")
                ref = ""
                if point.get("ref_min") and point.get("ref_max"):
                    ref = f" | норма: {point['ref_min']}–{point['ref_max']}"
                lines.append(f"{status_icon} {point['date']}: **{point['value']}** {point['unit']}{ref}")

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        else:
            # Показываем последние анализы профиля
            labs = db.query(LabResult).filter(
                LabResult.profile_id == profile.id
            ).order_by(LabResult.date.desc()).limit(5).all()

            if not labs:
                await update.message.reply_text(f"Для {profile.name} анализов пока нет. Отправьте фото анализа!")
                return

            lines = [f"🔬 **Анализы — {profile.name}**\n"]
            for lab in labs:
                abnormal = [m for m in (lab.markers or []) if m.get("status") not in ("normal", None)]
                status = f"⚠️ {len(abnormal)} вне нормы" if abnormal else "✅ норма"
                lines.append(f"• {lab.date.strftime('%d.%m.%Y')} — {lab.test_type or 'анализ'} ({status})")

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    finally:
        db.close()


async def cmd_growth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            "Использование:\n"
            "/рост [имя] — показать историю\n"
            "/рост [имя] [рост_см] [вес_кг] — записать новые данные\n"
            "Пример: /рост Лука 95 14.5"
        )
        return

    db = get_db()
    try:
        profile = get_profile_by_name(db, args[0])
        if not profile:
            await update.message.reply_text(f"Профиль '{args[0]}' не найден.")
            return

        if len(args) >= 3:
            # Записываем новые данные
            try:
                height = float(args[1].replace(",", "."))
                weight = float(args[2].replace(",", "."))
            except ValueError:
                await update.message.reply_text("Неверный формат. Пример: /рост Лука 95 14.5")
                return

            bmi = weight / ((height / 100) ** 2)
            record = GrowthRecord(
                profile_id=profile.id,
                date=date.today(),
                height_cm=height,
                weight_kg=weight,
                bmi=round(bmi, 1)
            )
            db.add(record)
            db.commit()

            age_info = calculate_age(profile.birthdate)
            report = format_growth_report(
                profile.name,
                age_info["years"],
                age_info["months"],
                height, weight,
                profile.gender or "male"
            )
            await update.message.reply_text(f"✅ Сохранено!\n\n{report}", parse_mode="Markdown")

        else:
            # Показываем историю
            records = db.query(GrowthRecord).filter(
                GrowthRecord.profile_id == profile.id
            ).order_by(GrowthRecord.date.desc()).limit(10).all()

            if not records:
                await update.message.reply_text(
                    f"Данных по росту/весу для {profile.name} нет.\n"
                    f"Добавьте: /рост {profile.name} [рост_см] [вес_кг]"
                )
                return

            lines = [f"📏 **История роста/веса — {profile.name}**\n"]
            for r in records:
                lines.append(f"• {r.date.strftime('%d.%m.%Y')}: {r.height_cm or '?'} см, {r.weight_kg or '?'} кг (ИМТ {r.bmi or '?'})")

            age_info = calculate_age(profile.birthdate)
            latest = records[0]
            if latest.height_cm and latest.weight_kg:
                report = format_growth_report(
                    profile.name, age_info["years"], age_info["months"],
                    latest.height_cm, latest.weight_kg, profile.gender or "male"
                )
                lines.append(f"\n{report}")

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    finally:
        db.close()


async def cmd_vaccines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /прививки [имя]\nПример: /прививки Аня")
        return

    db = get_db()
    try:
        profile = get_profile_by_name(db, args[0])
        if not profile:
            await update.message.reply_text(f"Профиль '{args[0]}' не найден.")
            return

        if not profile.is_child:
            await update.message.reply_text("Календарь прививок доступен только для детских профилей.")
            return

        vaccines_raw = db.query(Vaccine).filter(Vaccine.profile_id == profile.id).all()
        vaccines_list = [{"name": v.name, "date_given": v.date_given, "is_completed": v.is_completed} for v in vaccines_raw]

        vaccine_data = get_due_vaccines(profile.birthdate, vaccines_list)
        report = format_vaccine_report(profile.name, vaccine_data)

        await update.message.reply_text(report, parse_mode="Markdown")
    finally:
        db.close()


async def cmd_consilium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Использование: /консилиум [имя] [проблема]\n"
            "Пример: /консилиум София частые простуды"
        )
        return

    name = args[0]
    problem = " ".join(args[1:])

    db = get_db()
    try:
        profile = get_profile_by_name(db, name)
        if not profile:
            await update.message.reply_text(f"Профиль '{name}' не найден.")
            return

        await update.message.reply_text(
            f"🔄 Запускаю консилиум по '{problem}' для {profile.name}...\n"
            f"Это займёт 30-60 секунд, агенты работают параллельно."
        )

        profile_dict = {
            "name": profile.name,
            "birthdate": profile.birthdate,
            "gender": profile.gender,
            "blood_type": profile.blood_type,
            "is_child": profile.is_child,
            "allergies": profile.allergies or [],
            "chronic_conditions": profile.chronic_conditions or [],
            "family_history": profile.family_history or {},
        }

        context_str = build_profile_context(db, profile)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            run_consilium,
            profile_dict, context_str, problem
        )

        # Разбиваем длинный результат на части
        MAX_LEN = 4000
        if len(result) <= MAX_LEN:
            await update.message.reply_text(f"🏥 **Консилиум — {profile.name}**\n\n{result}", parse_mode="Markdown")
        else:
            chunks = [result[i:i+MAX_LEN] for i in range(0, len(result), MAX_LEN)]
            for i, chunk in enumerate(chunks):
                prefix = f"🏥 **Консилиум — {profile.name}** (часть {i+1}/{len(chunks)})\n\n" if i == 0 else ""
                await update.message.reply_text(f"{prefix}{chunk}", parse_mode="Markdown")

    finally:
        db.close()


async def cmd_doctor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Использование:\n"
            "/врач [имя] подготовь к [специальность] — чеклист для визита\n"
            "/врач [имя] был у [специальность] [диагноз] — записать визит\n"
            "Пример: /врач Аня подготовь к лору"
        )
        return

    db = get_db()
    try:
        profile = get_profile_by_name(db, args[0])
        if not profile:
            await update.message.reply_text(f"Профиль '{args[0]}' не найден.")
            return

        action_text = " ".join(args[1:]).lower()

        if action_text.startswith("подготовь"):
            specialty = action_text.replace("подготовь", "").replace("к", "").strip()
            context_str = build_profile_context(db, profile)

            await update.message.reply_text(f"⏳ Готовлю чеклист к {specialty} для {profile.name}...")

            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
            age_info = calculate_age(profile.birthdate)
            age_str = f"{age_info['years']} лет {age_info['months']} мес." if profile.is_child else f"{age_info['years']} лет"

            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": f"""Ты — опытный медицинский консультант.
Подготовь чеклист для визита к {specialty} для пациента {profile.name}, {age_str}.

ДАННЫЕ ПАЦИЕНТА:
{context_str}

Составь на русском языке:
1. **Что взять с собой** (анализы, направления, полис)
2. **Что спросить у врача** (конкретные вопросы)
3. **Что рассказать врачу** (ключевые жалобы/симптомы из истории)
4. **Какие анализы обсудить** (если есть отклонения в истории)

Формат: чёткий список, без лишних слов. Не более 20 пунктов суммарно."""
                }]
            )

            await update.message.reply_text(
                f"📋 **Чеклист к {specialty} — {profile.name}**\n\n{response.content[0].text}",
                parse_mode="Markdown"
            )

        elif "был у" in action_text or "была у" in action_text:
            # Записать визит — запрашиваем детали
            context.user_data["pending_visit"] = {
                "profile_id": profile.id,
                "profile_name": profile.name,
                "raw": action_text
            }
            await update.message.reply_text(
                f"Записываю визит для {profile.name}.\n\n"
                "Пришлите детали в формате:\n"
                "Специальность: ЛОР\n"
                "Врач: Иванов А.А.\n"
                "Диагноз: Острый тонзиллит\n"
                "Назначения: амоксициллин 250мг 3 раза в день 7 дней\n"
                "Рекомендации: повторный осмотр через 10 дней"
            )
        else:
            await update.message.reply_text("Не понял команду. Используйте 'подготовь к [специальность]' или 'был у [специальность]'")
    finally:
        db.close()


async def cmd_medication(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_auth(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /лекарство [имя]\nДалее введите детали препарата.")
        return

    db = get_db()
    try:
        profile = get_profile_by_name(db, args[0])
        if not profile:
            await update.message.reply_text(f"Профиль '{args[0]}' не найден.")
            return

        active_meds = db.query(Medication).filter(
            Medication.profile_id == profile.id,
            Medication.is_active == True
        ).all()

        if active_meds:
            lines = [f"💊 **Текущие лекарства — {profile.name}**\n"]
            for med in active_meds:
                start = med.start_date.strftime('%d.%m') if med.start_date else "?"
                end = med.end_date.strftime('%d.%m') if med.end_date else "бессрочно"
                lines.append(f"• **{med.name}** {med.dosage or ''} {med.frequency or ''} ({start}–{end})")
                if med.reason:
                    lines.append(f"  Причина: {med.reason}")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        else:
            await update.message.reply_text(f"У {profile.name} нет активных лекарств.")

        context.user_data["add_med_profile"] = profile.id
        await update.message.reply_text(
            f"Чтобы добавить лекарство для {profile.name}, напишите:\n"
            f"`+лекарство Название | дозировка | частота | причина`\n"
            f"Пример: `+лекарство амоксициллин | 250мг | 3 раза в день | ангина`",
            parse_mode="Markdown"
        )
    finally:
        db.close()


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает фото анализа."""
    if not check_auth(update.effective_user.id):
        return

    # Определяем профиль из caption или спрашиваем
    caption = update.message.caption or ""
    db = get_db()
    try:
        profile = None
        if caption:
            words = caption.split()
            if words:
                profile = get_profile_by_name(db, words[0])

        if not profile:
            # Спрашиваем для кого
            context.user_data["pending_lab_photo"] = update.message.photo[-1].file_id
            await update.message.reply_text(
                "Для кого этот анализ? Выберите профиль:",
                reply_markup=get_profile_keyboard(db)
            )
            return

        await _process_lab_photo(update, context, db, profile, update.message.photo[-1].file_id)
    finally:
        db.close()


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает PDF-документы."""
    if not check_auth(update.effective_user.id):
        return

    doc = update.message.document
    if not doc.mime_type in ("image/jpeg", "image/png", "application/pdf", "image/webp"):
        await update.message.reply_text("Поддерживаются: JPG, PNG, PDF, WebP")
        return

    caption = update.message.caption or ""
    db = get_db()
    try:
        profile = None
        if caption:
            words = caption.split()
            if words:
                profile = get_profile_by_name(db, words[0])

        if not profile:
            context.user_data["pending_lab_doc"] = doc.file_id
            context.user_data["pending_lab_mime"] = doc.mime_type
            await update.message.reply_text(
                "Для кого этот документ? Выберите профиль:",
                reply_markup=get_profile_keyboard(db)
            )
            return

        await _process_lab_document(update, context, db, profile, doc.file_id, doc.mime_type)
    finally:
        db.close()


async def _process_lab_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session, profile: Profile, file_id: str):
    """Распознаёт и сохраняет анализ из фото."""
    await update.message.reply_text(f"🔍 Распознаю анализ для {profile.name}...")

    photo_file = await context.bot.get_file(file_id)
    image_bytes = await photo_file.download_as_bytearray()

    loop = asyncio.get_event_loop()
    parsed = await loop.run_in_executor(None, parse_lab_from_image, bytes(image_bytes), "image/jpeg")

    # Сохраняем в БД
    lab_date = date.today()
    if parsed.get("date"):
        try:
            lab_date = datetime.strptime(parsed["date"], "%Y-%m-%d").date()
        except ValueError:
            pass

    lab = LabResult(
        profile_id=profile.id,
        date=lab_date,
        lab_name=parsed.get("lab_name"),
        test_type=parsed.get("test_type"),
        markers=parsed.get("markers", []),
        raw_text=parsed.get("raw_notes", ""),
    )
    db.add(lab)
    db.commit()

    summary = format_lab_summary(parsed, profile.name)
    await update.message.reply_text(f"✅ Сохранено!\n\n{summary}", parse_mode="Markdown")


async def _process_lab_document(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session, profile: Profile, file_id: str, mime_type: str):
    """Распознаёт и сохраняет анализ из документа."""
    await update.message.reply_text(f"🔍 Обрабатываю документ для {profile.name}...")

    doc_file = await context.bot.get_file(file_id)
    file_bytes = await doc_file.download_as_bytearray()

    loop = asyncio.get_event_loop()

    if mime_type == "application/pdf":
        # Конвертируем PDF в текст
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(bytes(file_bytes))) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            parsed = await loop.run_in_executor(None, parse_lab_from_text, text)
        except Exception:
            parsed = await loop.run_in_executor(None, parse_lab_from_image, bytes(file_bytes), "image/jpeg")
    else:
        parsed = await loop.run_in_executor(None, parse_lab_from_image, bytes(file_bytes), mime_type)

    lab_date = date.today()
    if parsed.get("date"):
        try:
            lab_date = datetime.strptime(parsed["date"], "%Y-%m-%d").date()
        except ValueError:
            pass

    lab = LabResult(
        profile_id=profile.id,
        date=lab_date,
        lab_name=parsed.get("lab_name"),
        test_type=parsed.get("test_type"),
        markers=parsed.get("markers", []),
        raw_text=parsed.get("raw_notes", ""),
    )
    db.add(lab)
    db.commit()

    summary = format_lab_summary(parsed, profile.name)
    await update.message.reply_text(f"✅ Сохранено!\n\n{summary}", parse_mode="Markdown")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия inline-кнопок."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("profile_"):
        profile_id = int(query.data.split("_")[1])
        db = get_db()
        try:
            profile = db.query(Profile).filter(Profile.id == profile_id).first()
            if not profile:
                await query.edit_message_text("Профиль не найден.")
                return

            # Проверяем, есть ли ожидающее фото или документ
            if "pending_lab_photo" in context.user_data:
                file_id = context.user_data.pop("pending_lab_photo")
                await query.edit_message_text(f"Обрабатываю анализ для {profile.name}...")
                await _process_lab_photo(query, context, db, profile, file_id)

            elif "pending_lab_doc" in context.user_data:
                file_id = context.user_data.pop("pending_lab_doc")
                mime_type = context.user_data.pop("pending_lab_mime", "image/jpeg")
                await query.edit_message_text(f"Обрабатываю документ для {profile.name}...")
                await _process_lab_document(query, context, db, profile, file_id, mime_type)

            else:
                # Просто показываем профиль
                age_info = calculate_age(profile.birthdate)
                await query.edit_message_text(
                    f"Выбран профиль: **{profile.name}** ({age_info['years']} лет)\n"
                    "Используйте /labs, /консилиум, /рост, /прививки",
                    parse_mode="Markdown"
                )
        finally:
            db.close()


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения — записи визитов и лекарств."""
    if not check_auth(update.effective_user.id):
        return

    text = update.message.text.strip()

    # Добавление лекарства
    if text.startswith("+лекарство") and "add_med_profile" in context.user_data:
        db = get_db()
        try:
            parts = text.replace("+лекарство", "").strip().split("|")
            if len(parts) >= 1:
                profile_id = context.user_data.pop("add_med_profile")
                med = Medication(
                    profile_id=profile_id,
                    name=parts[0].strip(),
                    dosage=parts[1].strip() if len(parts) > 1 else None,
                    frequency=parts[2].strip() if len(parts) > 2 else None,
                    reason=parts[3].strip() if len(parts) > 3 else None,
                    start_date=date.today(),
                    is_active=True,
                )
                db.add(med)
                db.commit()
                await update.message.reply_text(f"💊 Лекарство '{med.name}' добавлено!")
            return
        finally:
            db.close()

    # Запись визита — многострочный формат
    if "pending_visit" in context.user_data:
        db = get_db()
        try:
            visit_data = context.user_data.pop("pending_visit")
            lines_dict = {}
            for line in text.split("\n"):
                if ":" in line:
                    key, _, val = line.partition(":")
                    lines_dict[key.strip().lower()] = val.strip()

            visit = DoctorVisit(
                profile_id=visit_data["profile_id"],
                date=date.today(),
                specialty=lines_dict.get("специальность", lines_dict.get("specialty", "")),
                doctor_name=lines_dict.get("врач", lines_dict.get("доктор", "")),
                diagnosis=lines_dict.get("диагноз", ""),
                prescriptions=[lines_dict["назначения"]] if "назначения" in lines_dict else [],
                recommendations=lines_dict.get("рекомендации", ""),
            )
            db.add(visit)
            db.commit()

            await update.message.reply_text(
                f"✅ Визит записан для {visit_data['profile_name']}!\n"
                f"👨‍⚕️ {visit.specialty} — {visit.diagnosis or 'без диагноза'}"
            )
        finally:
            db.close()
        return

    # Если нет контекста — подсказка
    if not text.startswith("/"):
        await update.message.reply_text(
            "Отправьте фото анализа или используйте команды.\n"
            "Список команд: /start"
        )


def main():
    create_tables()

    # Импорт и запуск seed
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "models"))
        from models.profiles_seed import seed_profiles
        seed_profiles()
    except Exception as e:
        logger.warning(f"Seed profiles: {e}")

    app = Application.builder().token(TG_TOKEN).build()

    # Команды (русские и английские)
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler(["профиль", "profile", "кому"], cmd_profile))
    app.add_handler(CommandHandler(["labs", "анализы", "лабс"], cmd_labs))
    app.add_handler(CommandHandler(["рост", "growth", "вес"], cmd_growth))
    app.add_handler(CommandHandler(["прививки", "vaccines", "вакцины"], cmd_vaccines))
    app.add_handler(CommandHandler(["консилиум", "consilium", "анализ"], cmd_consilium))
    app.add_handler(CommandHandler(["врач", "doctor", "визит"], cmd_doctor))
    app.add_handler(CommandHandler(["лекарство", "medication", "мед"], cmd_medication))

    # Медиа
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Callback
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Health-OS Bot запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
