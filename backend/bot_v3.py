"""
Health-OS Telegram Bot v3
+ Долгосрочная память сессий
+ Голосовые сообщения (Whisper)
+ Умный анализ трендов
+ Проактивные уведомления (планировщик)
"""
import asyncio
import io
import json
import logging
import os
import sys
from datetime import date, datetime, time
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    CommandHandler,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "services"))

import anthropic
from models.database import (
    SessionLocal, Profile, LabResult, DoctorVisit,
    Medication, GrowthRecord, Vaccine, create_tables
)
from agents.lab_parser import parse_lab_from_image, format_lab_summary
from agents.base_agent import run_consilium, calculate_age
from agents.who_percentiles import format_growth_report
from agents.vaccines_calendar import get_due_vaccines, format_vaccine_report
from agents.trend_analyzer import format_trend_with_analysis, detect_anomalies_in_labs
from services.context_builder import build_profile_context, get_labs_trend
from services.session_memory import get_session, clear_old_sessions
from services.proactive import run_daily_check
from services.voice import transcribe_voice

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CLAUDE_KEY = os.getenv("CLAUDE_API_KEY")
ALLOWED_USER_IDS = set(
    int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()
)

claude = anthropic.Anthropic(api_key=CLAUDE_KEY)


# ── РОУТЕР ───────────────────────────────────────────────────────────────────

def build_router_system(session_context: str) -> str:
    base = """Ты — умный медицинский ассистент семьи. Определяй намерение по сообщению.

Члены семьи:
- Кирилл (папа, 36 лет, взрослый)
- София (дочь, 10 лет)
- Аня (дочь, 7 лет)
- Лука (сын, 3 года)
- Федор (сын, 7 мес.)

Намерения:
record_visit, record_lab, record_growth, record_medication, record_vaccine,
query_labs, query_visits, query_meds, query_growth, query_vaccines,
consilium, prep_visit, general_question, unknown

Верни ТОЛЬКО JSON:
{
  "intent": "...",
  "person": "имя или null",
  "details": { ... },
  "confidence": "high|medium|low"
}

Детали по намерениям:
- record_visit: specialty, doctor, diagnosis, prescriptions(list), recommendations, follow_up_date(YYYY-MM-DD)
- record_growth: height_cm, weight_kg
- record_medication: name, dosage, frequency, reason, duration_days
- record_vaccine: vaccine_name, date(YYYY-MM-DD)
- query_labs: marker_name (или null для общего запроса)
- consilium: problem
- prep_visit: specialty"""

    if session_context:
        base += f"\n\nКОНТЕКСТ ТЕКУЩЕГО РАЗГОВОРА:\n{session_context}\n\nЕсли person не указан явно — используй последнего упомянутого из контекста."

    return base


def build_chat_system(db_context: str) -> str:
    system = """Ты — тёплый семейный медицинский ассистент «Доктор Здоров».

Семья: Кирилл (папа, 36 л), София (10 л), Аня (7 л), Лука (3 г), Федор (7 мес.)

Правила:
- Говори по-русски, тепло и понятно
- НИКОГДА не ставь диагнозы — только «стоит обсудить с врачом»
- Будь кратким — 3-5 предложений если не просят подробнее
- Подтверждай сохранение кратко, добавляй полезный комментарий
- Один уточняющий вопрос если что-то непонятно"""

    if db_context:
        system += f"\n\nДАННЫЕ ИЗ МЕДКАРТЫ:\n{db_context}"

    return system


def get_db():
    return SessionLocal()


def get_profile_keyboard(db, label="Для кого?") -> InlineKeyboardMarkup:
    profiles = db.query(Profile).all()
    buttons = []
    row = []
    for p in profiles:
        row.append(InlineKeyboardButton(p.name, callback_data=f"sel_profile_{p.id}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def find_profile(db, name: str) -> Optional[Profile]:
    if not name:
        return None
    name_lower = name.lower().strip()
    for p in db.query(Profile).all():
        if p.name.lower().startswith(name_lower) or name_lower in p.name.lower():
            return p
    return None


async def route_message(text: str, session_context: str) -> dict:
    response = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system=build_router_system(session_context),
        messages=[{"role": "user", "content": text}]
    )
    raw = response.content[0].text
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"intent": "unknown", "person": None, "details": {}, "confidence": "low"}


async def generate_response(db_context: str, history: list, user_message: str, action_done: str = "") -> str:
    system = build_chat_system(db_context)
    messages = list(history)  # история разговора

    content = user_message
    if action_done:
        content = f"[Выполнено: {action_done}]\nСообщение пользователя: {user_message}"

    messages.append({"role": "user", "content": content})

    response = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system=system,
        messages=messages
    )
    return response.content[0].text


# ── ОБРАБОТЧИКИ ДЕЙСТВИЙ ─────────────────────────────────────────────────────

async def handle_record_visit(db, profile, details, text, history):
    visit = DoctorVisit(
        profile_id=profile.id,
        date=date.today(),
        specialty=details.get("specialty", ""),
        doctor_name=details.get("doctor", ""),
        diagnosis=details.get("diagnosis", ""),
        prescriptions=details.get("prescriptions", []),
        recommendations=details.get("recommendations", ""),
    )
    if details.get("follow_up_date"):
        try:
            visit.follow_up_date = datetime.strptime(details["follow_up_date"], "%Y-%m-%d").date()
        except Exception:
            pass

    db.add(visit)

    for prescription in details.get("prescriptions", []):
        if isinstance(prescription, str) and len(prescription) > 2:
            med = Medication(
                profile_id=profile.id,
                name=prescription,
                start_date=date.today(),
                is_active=True,
                reason=details.get("diagnosis", ""),
                prescribed_by=details.get("doctor", ""),
            )
            db.add(med)

    db.commit()

    action = f"Записан визит для {profile.name}: {details.get('specialty','врач')} — {details.get('diagnosis','')}"
    if details.get("prescriptions"):
        action += f". Назначено: {', '.join(str(p) for p in details['prescriptions'])}"
    if details.get("follow_up_date"):
        action += f". Повторный визит: {details['follow_up_date']}"

    return await generate_response("", history, text, action)


async def handle_record_growth(db, profile, details, text, history):
    height = details.get("height_cm")
    weight = details.get("weight_kg")

    record = GrowthRecord(
        profile_id=profile.id,
        date=date.today(),
        height_cm=float(height) if height else None,
        weight_kg=float(weight) if weight else None,
    )
    if height and weight:
        h = float(height) / 100
        record.bmi = round(float(weight) / (h * h), 1)

    db.add(record)
    db.commit()

    age_info = calculate_age(profile.birthdate)
    percentile_info = ""
    if height and weight:
        percentile_info = format_growth_report(
            profile.name, age_info["years"], age_info["months"],
            float(height), float(weight), profile.gender or "male"
        )

    action = f"Записан рост/вес для {profile.name}: {height} см, {weight} кг. {percentile_info}"
    return await generate_response("", history, text, action)


async def handle_record_medication(db, profile, details, text, history):
    from datetime import timedelta
    med = Medication(
        profile_id=profile.id,
        name=details.get("name", ""),
        dosage=details.get("dosage"),
        frequency=details.get("frequency"),
        reason=details.get("reason"),
        start_date=date.today(),
        is_active=True,
    )
    if details.get("duration_days"):
        med.end_date = date.today() + timedelta(days=int(details["duration_days"]))

    db.add(med)
    db.commit()

    action = f"Добавлено лекарство для {profile.name}: {med.name} {med.dosage or ''} {med.frequency or ''}"
    return await generate_response("", history, text, action)


async def handle_record_vaccine(db, profile, details, text, history):
    vaccine_date = date.today()
    if details.get("date"):
        try:
            vaccine_date = datetime.strptime(details["date"], "%Y-%m-%d").date()
        except Exception:
            pass

    v = Vaccine(
        profile_id=profile.id,
        name=details.get("vaccine_name", ""),
        date_given=vaccine_date,
        is_completed=True,
    )
    db.add(v)
    db.commit()

    action = f"Записана прививка для {profile.name}: {v.name}"
    return await generate_response("", history, text, action)


async def handle_query_labs(db, profile, details, text, history):
    marker_name = details.get("marker_name")

    if marker_name:
        trend = get_labs_trend(db, profile.id, marker_name)
        if trend:
            # Умный анализ тренда
            return format_trend_with_analysis(
                marker_name, trend, profile.name, profile.is_child
            )
        else:
            return f"По показателю «{marker_name}» для {profile.name} данных пока нет. Скинь фото анализа — сохраню."
    else:
        labs = db.query(LabResult).filter(
            LabResult.profile_id == profile.id
        ).order_by(LabResult.date.desc()).limit(5).all()

        if not labs:
            return f"Для {profile.name} анализов пока нет. Сфотографируй бланк и скинь — я распознаю и сохраню."

        ctx = build_profile_context(db, profile, limit_labs=5)
        return await generate_response(ctx, history, text)


# ── ГЛАВНЫЙ ОБРАБОТЧИК ТЕКСТА ─────────────────────────────────────────────────

async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, from_voice: bool = False):
    """Единая точка обработки — и текст, и голос."""
    user_id = update.effective_user.id
    session = get_session(user_id)
    session.add_message("user", text)

    db = get_db()
    thinking = await update.message.reply_text("⏳")

    try:
        # Роутер с контекстом сессии
        session_ctx = session.get_context_summary()
        loop = asyncio.get_event_loop()
        routed = await loop.run_in_executor(
            None, lambda: asyncio.run(route_message(text, session_ctx))
        )

        intent = routed.get("intent", "unknown")
        details = routed.get("details", {})
        person_name = routed.get("person")

        # Находим профиль — сначала из роутера, потом из памяти сессии
        profile = find_profile(db, person_name) if person_name else None
        if not profile and session.active_person:
            profile = find_profile(db, session.active_person)

        # Запоминаем активного человека
        if profile:
            session.set_active_person(profile.name)

        # Если профиль нужен но не найден — спрашиваем
        intents_needing_person = {
            "record_visit", "record_lab", "record_growth", "record_medication",
            "record_vaccine", "query_labs", "query_visits", "query_growth",
            "query_vaccines", "query_meds", "consilium", "prep_visit"
        }

        if intent in intents_needing_person and not profile:
            context.user_data["pending_intent"] = routed
            context.user_data["pending_text"] = text
            await thinking.edit_text("Для кого это?", reply_markup=get_profile_keyboard(db))
            db.close()
            return

        history = session.get_history_for_claude()[:-1]  # без последнего (уже в process)
        response = ""

        if intent == "record_visit" and profile:
            response = await handle_record_visit(db, profile, details, text, history)
        elif intent == "record_growth" and profile:
            response = await handle_record_growth(db, profile, details, text, history)
        elif intent == "record_medication" and profile:
            response = await handle_record_medication(db, profile, details, text, history)
        elif intent == "record_vaccine" and profile:
            response = await handle_record_vaccine(db, profile, details, text, history)
        elif intent == "query_labs" and profile:
            response = await handle_query_labs(db, profile, details, text, history)

        elif intent == "query_growth" and profile:
            records = db.query(GrowthRecord).filter(
                GrowthRecord.profile_id == profile.id
            ).order_by(GrowthRecord.date.desc()).limit(5).all()
            if records:
                age_info = calculate_age(profile.birthdate)
                latest = records[0]
                report = format_growth_report(
                    profile.name, age_info["years"], age_info["months"],
                    latest.height_cm, latest.weight_kg, profile.gender or "male"
                )
                history_lines = [f"• {r.date.strftime('%d.%m.%Y')}: {r.height_cm} см, {r.weight_kg} кг" for r in records]
                response = f"{report}\n\nИстория:\n" + "\n".join(history_lines)
            else:
                response = f"Данных по росту/весу для {profile.name} нет. Напиши например: «Лука 95 см 14 кг»"

        elif intent == "query_vaccines" and profile:
            vaccines_raw = db.query(Vaccine).filter(Vaccine.profile_id == profile.id).all()
            vaccines_list = [{"name": v.name, "date_given": v.date_given, "is_completed": v.is_completed} for v in vaccines_raw]
            vaccine_data = get_due_vaccines(profile.birthdate, vaccines_list)
            response = format_vaccine_report(profile.name, vaccine_data)

        elif intent == "query_meds" and profile:
            active = db.query(Medication).filter(
                Medication.profile_id == profile.id, Medication.is_active == True
            ).all()
            if active:
                lines = [f"💊 *Лекарства — {profile.name}*\n"]
                for m in active:
                    end = f" до {m.end_date.strftime('%d.%m')}" if m.end_date else ""
                    lines.append(f"• {m.name} {m.dosage or ''} {m.frequency or ''}{end}")
                    if m.reason:
                        lines.append(f"  _{m.reason}_")
                response = "\n".join(lines)
            else:
                response = f"У {profile.name} сейчас нет активных лекарств."

        elif intent == "query_visits" and profile:
            ctx = build_profile_context(db, profile, limit_labs=0, limit_visits=5)
            response = await generate_response(ctx, history, text)

        elif intent == "consilium" and profile:
            await thinking.edit_text(
                f"🔄 Запускаю анализ для {profile.name}...\n"
                "Работают специалисты параллельно, около минуты."
            )
            problem = details.get("problem", text)
            ctx = build_profile_context(db, profile)
            profile_dict = {
                "name": profile.name, "birthdate": profile.birthdate,
                "gender": profile.gender, "blood_type": profile.blood_type,
                "is_child": profile.is_child, "allergies": profile.allergies or [],
                "chronic_conditions": profile.chronic_conditions or [],
                "family_history": profile.family_history or {},
            }
            response = await loop.run_in_executor(
                None, run_consilium, profile_dict, ctx, problem
            )

        elif intent == "prep_visit" and profile:
            specialty = details.get("specialty", "врача")
            await thinking.edit_text(f"⏳ Готовлю чеклист к {specialty}...")
            ctx = build_profile_context(db, profile)
            age_info = calculate_age(profile.birthdate)
            prep = claude.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1500,
                messages=[{"role": "user", "content":
                    f"Подготовь чеклист к {specialty} для {profile.name}, {age_info['years']} лет.\n\nДАННЫЕ:\n{ctx}\n\n"
                    "Составь:\n1. Что взять с собой\n2. Что рассказать врачу\n3. Что спросить\n4. Какие анализы обсудить\n\nКратко, по делу."}]
            )
            response = f"📋 *Чеклист к {specialty} — {profile.name}*\n\n{prep.content[0].text}"

        else:
            ctx = build_profile_context(db, profile) if profile else ""
            response = await generate_response(ctx, history, text)

        # Сохраняем ответ в память
        session.add_message("assistant", response[:500])

        await thinking.delete()

        # Отправляем (разбиваем если длинный)
        MAX = 4000
        if len(response) <= MAX:
            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            for i in range(0, len(response), MAX):
                await update.message.reply_text(response[i:i+MAX], parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        try:
            await thinking.edit_text("Что-то пошло не так, попробуй ещё раз 🙏")
        except Exception:
            await update.message.reply_text("Что-то пошло не так, попробуй ещё раз 🙏")
    finally:
        db.close()


# ── HANDLERS ─────────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS:
        return
    await process_text(update, context, update.message.text.strip())


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Голосовое сообщение → Whisper → текст → обработка."""
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS:
        return

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        await update.message.reply_text(
            "Голосовые сообщения пока не подключены.\n"
            "Добавь OPENAI_API_KEY в переменные Railway — и заработает."
        )
        return

    thinking = await update.message.reply_text("🎙 Распознаю голосовое...")

    try:
        voice_file = await update.message.voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()

        text = await transcribe_voice(bytes(audio_bytes), "audio/ogg")
        await thinking.edit_text(f"🎙 _Распознано:_ {text}", parse_mode="Markdown")

        # Обрабатываем как текст
        await process_text(update, context, text, from_voice=True)

    except Exception as e:
        logger.error(f"Ошибка голосового: {e}")
        await thinking.edit_text("Не смог распознать голосовое. Попробуй написать текстом.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS:
        return

    caption = update.message.caption or ""
    db = get_db()
    try:
        profile = None
        user_id = update.effective_user.id
        session = get_session(user_id)

        # Сначала из caption, потом из памяти сессии
        if caption:
            profile = find_profile(db, caption.split()[0])
        if not profile and session.active_person:
            profile = find_profile(db, session.active_person)

        if not profile:
            context.user_data["pending_lab_photo"] = update.message.photo[-1].file_id
            await update.message.reply_text(
                "Это анализ для кого?",
                reply_markup=get_profile_keyboard(db)
            )
            return

        await _process_lab_photo(update, context, db, profile, update.message.photo[-1].file_id)
    finally:
        db.close()


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS:
        return

    doc = update.message.document
    if doc.mime_type not in ("image/jpeg", "image/png", "image/webp", "application/pdf"):
        await update.message.reply_text("Поддерживаю: JPG, PNG, PDF, WebP")
        return

    caption = update.message.caption or ""
    db = get_db()
    try:
        profile = None
        user_id = update.effective_user.id
        session = get_session(user_id)

        if caption:
            profile = find_profile(db, caption.split()[0])
        if not profile and session.active_person:
            profile = find_profile(db, session.active_person)

        if not profile:
            context.user_data["pending_lab_doc"] = doc.file_id
            context.user_data["pending_lab_mime"] = doc.mime_type
            await update.message.reply_text(
                "Это анализ для кого?",
                reply_markup=get_profile_keyboard(db)
            )
            return

        await _process_lab_document(update, context, db, profile, doc.file_id, doc.mime_type)
    finally:
        db.close()


async def _process_lab_photo(update_or_query, context, db, profile, file_id):
    try:
        msg = getattr(update_or_query, 'message', update_or_query)
    except Exception:
        msg = update_or_query

    thinking = await msg.reply_text(f"🔍 Читаю анализ для {profile.name}...")
    try:
        photo_file = await context.bot.get_file(file_id)
        image_bytes = await photo_file.download_as_bytearray()

        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(
            None, parse_lab_from_image, bytes(image_bytes), "image/jpeg"
        )

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

        # Умный анализ аномалий
        anomaly_comment = ""
        if parsed.get("markers"):
            anomaly_comment = detect_anomalies_in_labs(
                parsed["markers"], profile.name, profile.is_child
            )

        full_text = f"✅ Сохранено!\n\n{summary}"
        if anomaly_comment:
            full_text += f"\n\n{anomaly_comment}"

        await thinking.edit_text(full_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Lab photo error: {e}")
        await thinking.edit_text("Не смог распознать. Попробуй более чёткое фото.")


async def _process_lab_document(update_or_query, context, db, profile, file_id, mime_type):
    try:
        msg = getattr(update_or_query, 'message', update_or_query)
    except Exception:
        msg = update_or_query

    thinking = await msg.reply_text(f"🔍 Читаю документ для {profile.name}...")
    try:
        doc_file = await context.bot.get_file(file_id)
        file_bytes = await doc_file.download_as_bytearray()

        loop = asyncio.get_event_loop()

        if mime_type == "application/pdf":
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(bytes(file_bytes))) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                from agents.lab_parser import parse_lab_from_text
                parsed = await loop.run_in_executor(None, parse_lab_from_text, text)
            except Exception:
                parsed = await loop.run_in_executor(
                    None, parse_lab_from_image, bytes(file_bytes), "image/jpeg"
                )
        else:
            parsed = await loop.run_in_executor(
                None, parse_lab_from_image, bytes(file_bytes), mime_type
            )

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
        anomaly_comment = ""
        if parsed.get("markers"):
            anomaly_comment = detect_anomalies_in_labs(
                parsed["markers"], profile.name, profile.is_child
            )

        full_text = f"✅ Сохранено!\n\n{summary}"
        if anomaly_comment:
            full_text += f"\n\n{anomaly_comment}"

        await thinking.edit_text(full_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Lab doc error: {e}")
        await thinking.edit_text("Не смог обработать. Попробуй ещё раз.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("sel_profile_"):
        return

    profile_id = int(query.data.split("_")[-1])
    db = get_db()
    try:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            await query.edit_message_text("Профиль не найден")
            return

        # Запоминаем в сессию
        user_id = update.effective_user.id
        session = get_session(user_id)
        session.set_active_person(profile.name)

        if "pending_lab_photo" in context.user_data:
            file_id = context.user_data.pop("pending_lab_photo")
            await query.edit_message_text(f"Обрабатываю для {profile.name}...")
            await _process_lab_photo(query, context, db, profile, file_id)
            return

        if "pending_lab_doc" in context.user_data:
            file_id = context.user_data.pop("pending_lab_doc")
            mime = context.user_data.pop("pending_lab_mime", "image/jpeg")
            await query.edit_message_text(f"Обрабатываю для {profile.name}...")
            await _process_lab_document(query, context, db, profile, file_id, mime)
            return

        if "pending_intent" in context.user_data:
            routed = context.user_data.pop("pending_intent")
            original_text = context.user_data.pop("pending_text", "")
            await query.edit_message_text(f"Понял, это для {profile.name}. Секунду...")

            intent = routed.get("intent", "unknown")
            details = routed.get("details", {})
            history = session.get_history_for_claude()

            response = ""
            if intent == "record_visit":
                response = await handle_record_visit(db, profile, details, original_text, history)
            elif intent == "record_growth":
                response = await handle_record_growth(db, profile, details, original_text, history)
            elif intent == "record_medication":
                response = await handle_record_medication(db, profile, details, original_text, history)
            elif intent == "record_vaccine":
                response = await handle_record_vaccine(db, profile, details, original_text, history)
            elif intent == "query_labs":
                response = await handle_query_labs(db, profile, details, original_text, history)
            elif intent == "consilium":
                problem = details.get("problem", original_text)
                ctx = build_profile_context(db, profile)
                profile_dict = {
                    "name": profile.name, "birthdate": profile.birthdate,
                    "gender": profile.gender, "blood_type": profile.blood_type,
                    "is_child": profile.is_child, "allergies": profile.allergies or [],
                    "chronic_conditions": profile.chronic_conditions or [],
                    "family_history": profile.family_history or {},
                }
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, run_consilium, profile_dict, ctx, problem)
            else:
                ctx = build_profile_context(db, profile)
                response = await generate_response(ctx, history, original_text)

            session.add_message("assistant", response[:500])
            await query.message.reply_text(response, parse_mode="Markdown")
            return

        age_info = calculate_age(profile.birthdate)
        await query.edit_message_text(
            f"Выбран: *{profile.name}*, {age_info['years']} лет\nТеперь пиши — я всё пойму 👍",
            parse_mode="Markdown"
        )
    finally:
        db.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет\\! Я *Доктор Здоров* 🏥\n\n"
        "Пиши мне как другу:\n\n"
        "• _«Аня была у лора, тонзиллит, мирамистин»_\n"
        "• _«Лука 95 см, 14 кг»_\n"
        "• _«Покажи анализы крови Кирилла»_\n"
        "• _«Когда Феде делали прививки?»_\n"
        "• Скинь фото анализа — распознаю сам\n"
        "• 🎙 Отправь голосовое — тоже пойму\n\n"
        "Я помню о ком мы говорили — не нужно каждый раз называть имя 👌",
        parse_mode="MarkdownV2"
    )


# ── ПЛАНИРОВЩИК УВЕДОМЛЕНИЙ ───────────────────────────────────────────────────

async def daily_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Запускается каждый день в 9:00 МСК."""
    logger.info("Запуск ежедневных уведомлений")
    try:
        await run_daily_check()
    except Exception as e:
        logger.error(f"Ошибка уведомлений: {e}")


async def cleanup_sessions(context: ContextTypes.DEFAULT_TYPE):
    """Чистит устаревшие сессии раз в час."""
    clear_old_sessions()


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    create_tables()
    try:
        from models.profiles_seed import seed_profiles
        seed_profiles()
    except Exception as e:
        logger.warning(f"Seed: {e}")

    app = Application.builder().token(TG_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Планировщик — уведомления каждый день в 6:00 UTC (9:00 МСК)
    app.job_queue.run_daily(daily_notifications, time=time(6, 0))
    # Чистка сессий каждый час
    app.job_queue.run_repeating(cleanup_sessions, interval=3600, first=3600)

    logger.info("Health-OS Bot v3 запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
