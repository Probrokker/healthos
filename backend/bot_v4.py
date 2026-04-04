"""
Health-OS Telegram Bot v4
Все возможности v3 +
6. Распознавание рецептов и выписок
7. Напоминания о лекарствах в конкретное время
8. Семейная аптечка
10. Экспорт медкарты в PDF
"""
import asyncio
import io
import json
import logging
import os
import sys
from datetime import date, datetime, time, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, CommandHandler,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "services"))

import anthropic
from models.database import (
    SessionLocal, Profile, LabResult, DoctorVisit, Medication,
    GrowthRecord, Vaccine, MedicationReminder, MedicineChest, create_tables
)
from agents.lab_parser import parse_lab_from_image, format_lab_summary
from agents.document_parser import (
    parse_document_from_image, format_document_summary, get_actions_from_document
)
from agents.base_agent import run_consilium, calculate_age
from agents.who_percentiles import format_growth_report
from agents.vaccines_calendar import get_due_vaccines, format_vaccine_report
from agents.trend_analyzer import format_trend_with_analysis, detect_anomalies_in_labs
from services.context_builder import build_profile_context, get_labs_trend
from services.session_memory import get_session, clear_old_sessions
from services.proactive import run_daily_check
from services.voice import transcribe_voice
from services.reminders import (
    parse_reminder_request, format_reminder_confirmation,
    send_medication_reminders, check_expiring_reminders
)
from services.medicine_chest import parse_chest_action, format_chest_list, generate_travel_pack
from services.pdf_export import generate_medical_card_pdf

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CLAUDE_KEY = os.getenv("CLAUDE_API_KEY")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")
ALLOWED_USER_IDS = set(int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip())

claude = anthropic.Anthropic(api_key=CLAUDE_KEY)


# ── РОУТЕР ────────────────────────────────────────────────────────────────────

ROUTER_SYSTEM_BASE = """Ты — умный медицинский ассистент семьи. Определяй намерение.

Семья: Кирилл (папа, 36л), София (10л), Аня (7л), Лука (3г), Федор (7мес.)

Намерения:
record_visit, record_lab, record_growth, record_medication, record_vaccine,
query_labs, query_visits, query_meds, query_growth, query_vaccines,
consilium, prep_visit,
set_reminder,           ← «напомни принять лекарство в 8 и 20»
chest_action,           ← «купил нурофен», «что есть от температуры», «что взять в поездку»
export_pdf,             ← «экспорт медкарты», «сделай PDF», «выгрузи карточку»
general_question, unknown

Верни ТОЛЬКО JSON:
{
  "intent": "...",
  "person": "имя или null",
  "details": { ... },
  "confidence": "high|medium|low"
}

Детали:
- record_visit: specialty, doctor, diagnosis, prescriptions(list), recommendations, follow_up_date(YYYY-MM-DD)
- record_growth: height_cm, weight_kg
- record_medication: name, dosage, frequency, reason, duration_days
- record_vaccine: vaccine_name, date(YYYY-MM-DD)
- query_labs: marker_name или null
- consilium: problem
- prep_visit: specialty
- set_reminder: (оставь пустым — парсим отдельно)
- chest_action: (оставь пустым — парсим отдельно)
- export_pdf: (оставь пустым)"""


def build_router_system(session_ctx: str) -> str:
    s = ROUTER_SYSTEM_BASE
    if session_ctx:
        s += f"\n\nКОНТЕКСТ РАЗГОВОРА:\n{session_ctx}\nЕсли person не указан — используй последнего упомянутого."
    return s


def build_chat_system(db_ctx: str) -> str:
    s = """Ты — тёплый семейный медицинский ассистент «Доктор Здоров».
Семья: Кирилл (папа, 36л), София (10л), Аня (7л), Лука (3г), Федор (7мес.)
Говори по-русски, тепло. НИКОГДА не ставь диагнозы. Будь кратким — 3-5 предложений."""
    if db_ctx:
        s += f"\n\nДАННЫЕ ИЗ МЕДКАРТЫ:\n{db_ctx}"
    return s


def get_db():
    return SessionLocal()


def find_profile(db, name: str) -> Optional[Profile]:
    if not name:
        return None
    nl = name.lower().strip()
    for p in db.query(Profile).all():
        if p.name.lower().startswith(nl) or nl in p.name.lower():
            return p
    return None


def get_profile_keyboard(db) -> InlineKeyboardMarkup:
    profiles = db.query(Profile).all()
    buttons, row = [], []
    for p in profiles:
        row.append(InlineKeyboardButton(p.name, callback_data=f"sel_profile_{p.id}"))
        if len(row) == 3:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def route_message(text: str, session_ctx: str) -> dict:
    resp = claude.messages.create(
        model="claude-sonnet-4-5", max_tokens=600,
        system=build_router_system(session_ctx),
        messages=[{"role": "user", "content": text}]
    )
    raw = resp.content[0].text
    try:
        s, e = raw.find("{"), raw.rfind("}") + 1
        return json.loads(raw[s:e])
    except Exception:
        return {"intent": "unknown", "person": None, "details": {}, "confidence": "low"}


async def gen_response(db_ctx: str, history: list, user_msg: str, action: str = "") -> str:
    msgs = list(history)
    content = f"[Выполнено: {action}]\nСообщение: {user_msg}" if action else user_msg
    msgs.append({"role": "user", "content": content})
    resp = claude.messages.create(
        model="claude-sonnet-4-5", max_tokens=600,
        system=build_chat_system(db_ctx), messages=msgs
    )
    return resp.content[0].text


# ── ОБРАБОТЧИКИ ДЕЙСТВИЙ ──────────────────────────────────────────────────────

async def do_record_visit(db, profile, details, text, history):
    visit = DoctorVisit(
        profile_id=profile.id, date=date.today(),
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
    for p in details.get("prescriptions", []):
        if isinstance(p, str) and len(p) > 2:
            db.add(Medication(profile_id=profile.id, name=p, start_date=date.today(),
                              is_active=True, reason=details.get("diagnosis", ""),
                              prescribed_by=details.get("doctor", "")))
    db.commit()
    action = f"Записан визит для {profile.name}: {details.get('specialty','врач')} — {details.get('diagnosis','')}"
    if details.get("prescriptions"):
        action += f". Назначено: {', '.join(str(p) for p in details['prescriptions'])}"
    if details.get("follow_up_date"):
        action += f". Повторный визит: {details['follow_up_date']}"
    return await gen_response("", history, text, action)


async def do_record_growth(db, profile, details, text, history):
    h, w = details.get("height_cm"), details.get("weight_kg")
    rec = GrowthRecord(profile_id=profile.id, date=date.today(),
                       height_cm=float(h) if h else None,
                       weight_kg=float(w) if w else None)
    if h and w:
        rec.bmi = round(float(w) / ((float(h)/100)**2), 1)
    db.add(rec); db.commit()
    age = calculate_age(profile.birthdate)
    report = format_growth_report(profile.name, age["years"], age["months"],
                                   float(h) if h else None, float(w) if w else None,
                                   profile.gender or "male") if h and w else ""
    return await gen_response("", history, text, f"Записан рост/вес для {profile.name}: {h}см, {w}кг. {report}")


async def do_record_medication(db, profile, details, text, history):
    med = Medication(profile_id=profile.id, name=details.get("name",""),
                     dosage=details.get("dosage"), frequency=details.get("frequency"),
                     reason=details.get("reason"), start_date=date.today(), is_active=True)
    if details.get("duration_days"):
        med.end_date = date.today() + timedelta(days=int(details["duration_days"]))
    db.add(med); db.commit()
    return await gen_response("", history, text,
        f"Добавлено лекарство для {profile.name}: {med.name} {med.dosage or ''} {med.frequency or ''}")


async def do_record_vaccine(db, profile, details, text, history):
    vdate = date.today()
    if details.get("date"):
        try: vdate = datetime.strptime(details["date"], "%Y-%m-%d").date()
        except Exception: pass
    db.add(Vaccine(profile_id=profile.id, name=details.get("vaccine_name",""),
                   date_given=vdate, is_completed=True))
    db.commit()
    return await gen_response("", history, text,
        f"Записана прививка для {profile.name}: {details.get('vaccine_name','')}")


async def do_query_labs(db, profile, details, text, history):
    marker = details.get("marker_name")
    if marker:
        trend = get_labs_trend(db, profile.id, marker)
        if trend:
            return format_trend_with_analysis(marker, trend, profile.name, profile.is_child)
        return f"По показателю «{marker}» для {profile.name} данных нет. Скинь фото анализа — сохраню."
    labs = db.query(LabResult).filter(LabResult.profile_id==profile.id).order_by(LabResult.date.desc()).limit(5).all()
    if not labs:
        return f"Для {profile.name} анализов пока нет. Сфотографируй бланк и скинь."
    return await gen_response(build_profile_context(db, profile, limit_labs=5), history, text)


async def do_set_reminder(db, profile, text, chat_id, history):
    """Создаёт напоминание о лекарстве."""
    reminder_data = parse_reminder_request(text, profile.name)
    if not reminder_data or not reminder_data.get("medication_name"):
        return "Не смог распознать лекарство и время. Напиши например: «напомни Луке амоксициллин в 8, 14 и 20 часов»"

    end_date = None
    if reminder_data.get("duration_days"):
        end_date = date.today() + timedelta(days=int(reminder_data["duration_days"]))

    reminder = MedicationReminder(
        profile_id=profile.id,
        medication_name=reminder_data["medication_name"],
        dosage=reminder_data.get("dosage"),
        times=reminder_data.get("times", []),
        start_date=date.today(),
        end_date=end_date,
        is_active=True,
        chat_id=str(chat_id),
    )
    db.add(reminder); db.commit()
    return format_reminder_confirmation(reminder_data, profile.name, end_date)


async def do_chest_action(db, text, profile: Optional[Profile], history):
    """Действие с аптечкой."""
    parsed = parse_chest_action(text)
    action = parsed.get("action", "query")
    item_data = parsed.get("item", {})

    if action == "add" and item_data.get("name"):
        expiry = None
        if item_data.get("expiry_date"):
            try: expiry = datetime.strptime(item_data["expiry_date"], "%Y-%m-%d").date()
            except Exception: pass
        med = MedicineChest(
            name=item_data["name"],
            form=item_data.get("form"),
            dosage=item_data.get("dosage"),
            quantity=item_data.get("quantity"),
            expiry_date=expiry,
            for_whom=item_data.get("for_whom", []),
            location=item_data.get("location"),
            is_available=True,
        )
        db.add(med); db.commit()
        return f"✅ Добавлено в аптечку: *{med.name}*{' ' + med.dosage if med.dosage else ''}{' (' + med.quantity + ')' if med.quantity else ''}"

    elif action == "remove" and item_data.get("name"):
        name_lower = item_data["name"].lower()
        item = db.query(MedicineChest).filter(
            MedicineChest.is_available == True
        ).all()
        found = next((i for i in item if name_lower in i.name.lower()), None)
        if found:
            found.is_available = False
            db.commit()
            return f"✅ Убрано из аптечки: *{found.name}*"
        return f"«{item_data['name']}» не нашёл в аптечке."

    elif action == "travel_pack":
        items = db.query(MedicineChest).filter(MedicineChest.is_available==True).all()
        children_ages = []
        profiles = db.query(Profile).filter(Profile.is_child==True).all()
        for p in profiles:
            age = calculate_age(p.birthdate)
            children_ages.append(age["years"])
        return generate_travel_pack(items, bool(profiles), children_ages)

    else:  # query
        query_text = parsed.get("query_text", "")
        all_items = db.query(MedicineChest).filter(MedicineChest.is_available==True).all()
        if query_text:
            ql = query_text.lower()
            filtered = [i for i in all_items if ql in i.name.lower() or
                        any(ql in w.lower() for w in (i.for_whom or []))]
            return format_chest_list(filtered, query_text)
        return format_chest_list(all_items)


async def do_export_pdf(db, profile, context_bot) -> tuple:
    """Генерирует PDF и возвращает (bytes, filename)."""
    labs = db.query(LabResult).filter(LabResult.profile_id==profile.id).order_by(LabResult.date.desc()).limit(20).all()
    visits = db.query(DoctorVisit).filter(DoctorVisit.profile_id==profile.id).order_by(DoctorVisit.date.desc()).limit(30).all()
    meds = db.query(Medication).filter(Medication.profile_id==profile.id).all()
    growth = db.query(GrowthRecord).filter(GrowthRecord.profile_id==profile.id).order_by(GrowthRecord.date.desc()).all()
    vaccines = db.query(Vaccine).filter(Vaccine.profile_id==profile.id).all()

    pdf_bytes = generate_medical_card_pdf(profile, labs, visits, meds, growth, vaccines)
    filename = f"medcard_{profile.name}_{date.today().strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


# ── ГЛАВНЫЙ ОБРАБОТЧИК ────────────────────────────────────────────────────────

async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    session = get_session(user_id)
    session.add_message("user", text)

    db = get_db()
    thinking = await update.message.reply_text("⏳")

    try:
        session_ctx = session.get_context_summary()
        loop = asyncio.get_event_loop()
        routed = await loop.run_in_executor(None, lambda: asyncio.run(route_message(text, session_ctx)))

        intent = routed.get("intent", "unknown")
        details = routed.get("details", {})
        person_name = routed.get("person")

        profile = find_profile(db, person_name) if person_name else None
        if not profile and session.active_person:
            profile = find_profile(db, session.active_person)
        if profile:
            session.set_active_person(profile.name)

        intents_needing_person = {
            "record_visit", "record_lab", "record_growth", "record_medication",
            "record_vaccine", "query_labs", "query_visits", "query_growth",
            "query_vaccines", "query_meds", "consilium", "prep_visit",
            "set_reminder", "export_pdf"
        }

        if intent in intents_needing_person and not profile:
            context.user_data["pending_intent"] = routed
            context.user_data["pending_text"] = text
            await thinking.edit_text("Для кого это?", reply_markup=get_profile_keyboard(db))
            db.close(); return

        history = session.get_history_for_claude()[:-1]
        response = ""

        if intent == "record_visit" and profile:
            response = await do_record_visit(db, profile, details, text, history)
        elif intent == "record_growth" and profile:
            response = await do_record_growth(db, profile, details, text, history)
        elif intent == "record_medication" and profile:
            response = await do_record_medication(db, profile, details, text, history)
        elif intent == "record_vaccine" and profile:
            response = await do_record_vaccine(db, profile, details, text, history)
        elif intent == "query_labs" and profile:
            response = await do_query_labs(db, profile, details, text, history)
        elif intent == "query_growth" and profile:
            records = db.query(GrowthRecord).filter(GrowthRecord.profile_id==profile.id).order_by(GrowthRecord.date.desc()).limit(5).all()
            if records:
                age = calculate_age(profile.birthdate)
                r = records[0]
                report = format_growth_report(profile.name, age["years"], age["months"], r.height_cm, r.weight_kg, profile.gender or "male")
                hist = "\n".join(f"• {x.date.strftime('%d.%m.%Y')}: {x.height_cm}см, {x.weight_kg}кг" for x in records)
                response = f"{report}\n\nИстория:\n{hist}"
            else:
                response = f"Данных по росту для {profile.name} нет. Напиши: «Лука 95 см 14 кг»"
        elif intent == "query_vaccines" and profile:
            vraw = db.query(Vaccine).filter(Vaccine.profile_id==profile.id).all()
            vlist = [{"name": v.name, "date_given": v.date_given, "is_completed": v.is_completed} for v in vraw]
            response = format_vaccine_report(profile.name, get_due_vaccines(profile.birthdate, vlist))
        elif intent == "query_meds" and profile:
            active = db.query(Medication).filter(Medication.profile_id==profile.id, Medication.is_active==True).all()
            if active:
                lines = [f"💊 *Лекарства — {profile.name}*\n"]
                for m in active:
                    end = f" до {m.end_date.strftime('%d.%m')}" if m.end_date else ""
                    lines.append(f"• {m.name} {m.dosage or ''} {m.frequency or ''}{end}")
                    if m.reason: lines.append(f"  _{m.reason}_")
                response = "\n".join(lines)
            else:
                response = f"У {profile.name} нет активных лекарств."
        elif intent == "query_visits" and profile:
            ctx = build_profile_context(db, profile, limit_labs=0, limit_visits=5)
            response = await gen_response(ctx, history, text)
        elif intent == "consilium" and profile:
            await thinking.edit_text(f"🔄 Запускаю анализ для {profile.name}...\nОколо минуты.")
            problem = details.get("problem", text)
            ctx = build_profile_context(db, profile)
            pd = {"name": profile.name, "birthdate": profile.birthdate, "gender": profile.gender,
                  "blood_type": profile.blood_type, "is_child": profile.is_child,
                  "allergies": profile.allergies or [], "chronic_conditions": profile.chronic_conditions or [],
                  "family_history": profile.family_history or {}}
            response = await loop.run_in_executor(None, run_consilium, pd, ctx, problem)
        elif intent == "prep_visit" and profile:
            spec = details.get("specialty", "врача")
            await thinking.edit_text(f"⏳ Готовлю чеклист к {spec}...")
            ctx = build_profile_context(db, profile)
            age = calculate_age(profile.birthdate)
            r = claude.messages.create(model="claude-sonnet-4-5", max_tokens=1500,
                messages=[{"role": "user", "content":
                    f"Чеклист к {spec} для {profile.name}, {age['years']} лет.\n{ctx}\n\n"
                    "1. Что взять\n2. Что рассказать\n3. Что спросить\n4. Какие анализы обсудить\n\nКратко."}])
            response = f"📋 *Чеклист к {spec} — {profile.name}*\n\n{r.content[0].text}"

        elif intent == "set_reminder" and profile:
            response = await do_set_reminder(db, profile, text, chat_id, history)

        elif intent == "chest_action":
            response = await do_chest_action(db, text, profile, history)

        elif intent == "export_pdf" and profile:
            await thinking.edit_text(f"📄 Генерирую PDF медкарты для {profile.name}...")
            try:
                pdf_bytes, filename = await loop.run_in_executor(None, lambda: asyncio.run(do_export_pdf(db, profile, context.bot)))
                await thinking.delete()
                await update.message.reply_document(
                    document=io.BytesIO(pdf_bytes),
                    filename=filename,
                    caption=f"📋 Медкарта {profile.name} — {date.today().strftime('%d.%m.%Y')}"
                )
                session.add_message("assistant", f"Отправил PDF медкарты для {profile.name}")
                db.close(); return
            except ImportError:
                response = "PDF не работает — нужно добавить `reportlab` в requirements.txt и передеплоить."

        else:
            ctx = build_profile_context(db, profile) if profile else ""
            response = await gen_response(ctx, history, text)

        session.add_message("assistant", response[:500])
        await thinking.delete()

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
            await update.message.reply_text("Что-то пошло не так 🙏")
    finally:
        db.close()


# ── MEDIA HANDLERS ────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS: return
    await process_text(update, context, update.message.text.strip())


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS: return
    if not os.getenv("OPENAI_API_KEY"):
        await update.message.reply_text("Голосовые не подключены — добавь OPENAI_API_KEY в Railway.")
        return
    thinking = await update.message.reply_text("🎙 Распознаю...")
    try:
        vf = await update.message.voice.get_file()
        audio = await vf.download_as_bytearray()
        text = await transcribe_voice(bytes(audio), "audio/ogg")
        await thinking.edit_text(f"🎙 _{text}_", parse_mode="Markdown")
        await process_text(update, context, text)
    except Exception as e:
        logger.error(f"Voice error: {e}")
        await thinking.edit_text("Не смог распознать. Попробуй текстом.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS: return
    caption = update.message.caption or ""
    db = get_db()
    try:
        session = get_session(update.effective_user.id)
        profile = find_profile(db, caption.split()[0]) if caption else None
        if not profile and session.active_person:
            profile = find_profile(db, session.active_person)
        if not profile:
            context.user_data["pending_lab_photo"] = update.message.photo[-1].file_id
            await update.message.reply_text("Это для кого?", reply_markup=get_profile_keyboard(db))
            return
        await _process_photo(update, context, db, profile, update.message.photo[-1].file_id)
    finally:
        db.close()


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS: return
    doc = update.message.document
    if doc.mime_type not in ("image/jpeg","image/png","image/webp","application/pdf"): return
    caption = update.message.caption or ""
    db = get_db()
    try:
        session = get_session(update.effective_user.id)
        profile = find_profile(db, caption.split()[0]) if caption else None
        if not profile and session.active_person:
            profile = find_profile(db, session.active_person)
        if not profile:
            context.user_data["pending_lab_doc"] = doc.file_id
            context.user_data["pending_lab_mime"] = doc.mime_type
            await update.message.reply_text("Это для кого?", reply_markup=get_profile_keyboard(db))
            return
        await _process_doc(update, context, db, profile, doc.file_id, doc.mime_type)
    finally:
        db.close()


async def _process_photo(update_or_q, context, db, profile, file_id):
    msg = getattr(update_or_q, 'message', update_or_q)
    thinking = await msg.reply_text(f"🔍 Читаю для {profile.name}...")
    try:
        pf = await context.bot.get_file(file_id)
        img = await pf.download_as_bytearray()
        loop = asyncio.get_event_loop()

        # Пробуем определить тип документа — анализ или рецепт/выписка
        parsed_doc = await loop.run_in_executor(None, parse_document_from_image, bytes(img), "image/jpeg")
        doc_type = parsed_doc.get("document_type", "other")

        if doc_type == "analysis":
            # Обрабатываем как анализ
            parsed = await loop.run_in_executor(None, parse_lab_from_image, bytes(img), "image/jpeg")
            lab_date = date.today()
            if parsed.get("date"):
                try: lab_date = datetime.strptime(parsed["date"], "%Y-%m-%d").date()
                except ValueError: pass
            db.add(LabResult(profile_id=profile.id, date=lab_date,
                             lab_name=parsed.get("lab_name"), test_type=parsed.get("test_type"),
                             markers=parsed.get("markers", []), raw_text=parsed.get("raw_notes","")))
            db.commit()
            summary = format_lab_summary(parsed, profile.name)
            anomaly = detect_anomalies_in_labs(parsed.get("markers",[]), profile.name, profile.is_child) if parsed.get("markers") else ""
            full = f"✅ Сохранено!\n\n{summary}"
            if anomaly: full += f"\n\n{anomaly}"
            await thinking.edit_text(full, parse_mode="Markdown")
        else:
            # Обрабатываем как рецепт/выписку
            summary = format_document_summary(parsed_doc, profile.name)
            actions = get_actions_from_document(parsed_doc)

            if actions["save_visit"]:
                vd = actions["visit_data"]
                db.add(DoctorVisit(profile_id=profile.id, date=parsed_doc.get("date") and
                    datetime.strptime(parsed_doc["date"], "%Y-%m-%d").date() or date.today(),
                    specialty=vd.get("specialty",""), doctor_name=vd.get("doctor_name",""),
                    diagnosis=vd.get("diagnosis",""), recommendations=vd.get("recommendations","")))

            for med_data in actions["save_medications"]:
                db.add(Medication(profile_id=profile.id, name=med_data["name"],
                                  dosage=med_data.get("dosage"), frequency=med_data.get("frequency"),
                                  reason=med_data.get("reason",""), start_date=date.today(), is_active=True))
            db.commit()

            saved_info = ""
            if actions["save_visit"]: saved_info += " Визит сохранён."
            if actions["save_medications"]: saved_info += f" Лекарств добавлено: {len(actions['save_medications'])}."

            await thinking.edit_text(f"✅ Сохранено!{saved_info}\n\n{summary}", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Photo error: {e}")
        await thinking.edit_text("Не смог распознать. Попробуй более чёткое фото.")


async def _process_doc(update_or_q, context, db, profile, file_id, mime_type):
    msg = getattr(update_or_q, 'message', update_or_q)
    thinking = await msg.reply_text(f"🔍 Читаю документ для {profile.name}...")
    try:
        df = await context.bot.get_file(file_id)
        fbytes = await df.download_as_bytearray()
        loop = asyncio.get_event_loop()

        if mime_type == "application/pdf":
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(bytes(fbytes))) as pdf:
                    text = "\n".join(p.extract_text() or "" for p in pdf.pages)
                from agents.document_parser import parse_document_from_text
                parsed_doc = await loop.run_in_executor(None, parse_document_from_text, text)
            except Exception:
                parsed_doc = await loop.run_in_executor(None, parse_document_from_image, bytes(fbytes), "image/jpeg")
        else:
            parsed_doc = await loop.run_in_executor(None, parse_document_from_image, bytes(fbytes), mime_type)

        summary = format_document_summary(parsed_doc, profile.name)
        actions = get_actions_from_document(parsed_doc)

        if actions["save_visit"]:
            vd = actions["visit_data"]
            db.add(DoctorVisit(profile_id=profile.id, date=date.today(),
                               specialty=vd.get("specialty",""), doctor_name=vd.get("doctor_name",""),
                               diagnosis=vd.get("diagnosis",""), recommendations=vd.get("recommendations","")))
        for md in actions["save_medications"]:
            db.add(Medication(profile_id=profile.id, name=md["name"],
                              dosage=md.get("dosage"), frequency=md.get("frequency"),
                              reason=md.get("reason",""), start_date=date.today(), is_active=True))
        db.commit()

        saved = ""
        if actions["save_visit"]: saved += " Визит сохранён."
        if actions["save_medications"]: saved += f" Лекарств: {len(actions['save_medications'])}."
        await thinking.edit_text(f"✅ Сохранено!{saved}\n\n{summary}", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Doc error: {e}")
        await thinking.edit_text("Не смог обработать. Попробуй ещё раз.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("sel_profile_"): return

    profile_id = int(query.data.split("_")[-1])
    db = get_db()
    try:
        profile = db.query(Profile).filter(Profile.id==profile_id).first()
        if not profile:
            await query.edit_message_text("Профиль не найден"); return

        session = get_session(update.effective_user.id)
        session.set_active_person(profile.name)

        if "pending_lab_photo" in context.user_data:
            fid = context.user_data.pop("pending_lab_photo")
            await query.edit_message_text(f"Обрабатываю для {profile.name}...")
            await _process_photo(query, context, db, profile, fid); return

        if "pending_lab_doc" in context.user_data:
            fid = context.user_data.pop("pending_lab_doc")
            mime = context.user_data.pop("pending_lab_mime", "image/jpeg")
            await query.edit_message_text(f"Обрабатываю для {profile.name}...")
            await _process_doc(query, context, db, profile, fid, mime); return

        if "pending_intent" in context.user_data:
            routed = context.user_data.pop("pending_intent")
            orig = context.user_data.pop("pending_text", "")
            await query.edit_message_text(f"Понял, для {profile.name}. Секунду...")
            intent = routed.get("intent", "unknown")
            details = routed.get("details", {})
            history = session.get_history_for_claude()
            response = ""
            chat_id = update.effective_chat.id

            if intent == "record_visit": response = await do_record_visit(db, profile, details, orig, history)
            elif intent == "record_growth": response = await do_record_growth(db, profile, details, orig, history)
            elif intent == "record_medication": response = await do_record_medication(db, profile, details, orig, history)
            elif intent == "record_vaccine": response = await do_record_vaccine(db, profile, details, orig, history)
            elif intent == "query_labs": response = await do_query_labs(db, profile, details, orig, history)
            elif intent == "set_reminder": response = await do_set_reminder(db, profile, orig, chat_id, history)
            elif intent == "export_pdf":
                await query.message.reply_text(f"📄 Генерирую PDF для {profile.name}...")
                try:
                    loop = asyncio.get_event_loop()
                    pdf_bytes, filename = await loop.run_in_executor(None, lambda: asyncio.run(do_export_pdf(db, profile, context.bot)))
                    await query.message.reply_document(document=io.BytesIO(pdf_bytes), filename=filename,
                        caption=f"📋 Медкарта {profile.name} — {date.today().strftime('%d.%m.%Y')}")
                    db.close(); return
                except Exception as ex:
                    response = f"Ошибка PDF: {ex}"
            else:
                ctx = build_profile_context(db, profile)
                response = await gen_response(ctx, history, orig)

            session.add_message("assistant", response[:500])
            await query.message.reply_text(response, parse_mode="Markdown")
            return

        age = calculate_age(profile.birthdate)
        await query.edit_message_text(
            f"Выбран: *{profile.name}*, {age['years']} лет. Пиши — я всё пойму 👍",
            parse_mode="Markdown")
    finally:
        db.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет\\! Я *Доктор Здоров* 🏥\n\n"
        "Пиши как другу:\n\n"
        "• _«Аня была у лора, тонзиллит»_\n"
        "• _«Напомни Луке амоксициллин в 8, 14 и 20»_\n"
        "• _«Купил нурофен 200мг»_\n"
        "• _«Что взять в аптечку в поездку?»_\n"
        "• _«Сделай PDF медкарты Кирилла»_\n"
        "• Фото анализа, рецепта или выписки — распознаю сам\n"
        "• 🎙 Голосовое — тоже пойму",
        parse_mode="MarkdownV2"
    )


# ── ПЛАНИРОВЩИК ───────────────────────────────────────────────────────────────

async def job_daily(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Ежедневные уведомления")
    try:
        await run_daily_check()
    except Exception as e:
        logger.error(f"Daily job error: {e}")


async def job_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Каждую минуту проверяем напоминания."""
    db = get_db()
    try:
        await send_medication_reminders(context.bot, db)
    except Exception as e:
        logger.error(f"Reminder error: {e}")
    finally:
        db.close()


async def job_cleanup(context: ContextTypes.DEFAULT_TYPE):
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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # 9:00 МСК = 6:00 UTC
    app.job_queue.run_daily(job_daily, time=time(6, 0))
    # Напоминания о лекарствах — каждую минуту
    app.job_queue.run_repeating(job_reminders, interval=60, first=10)
    # Чистка сессий — каждый час
    app.job_queue.run_repeating(job_cleanup, interval=3600, first=3600)

    logger.info("Health-OS Bot v4 запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
