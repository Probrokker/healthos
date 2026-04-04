"""
Health-OS Telegram Bot v2 — свободный чат, никаких команд.
Claude сам понимает что написал пользователь и что нужно сделать.
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
    Medication, GrowthRecord, Vaccine, Hypothesis, create_tables
)
from agents.lab_parser import parse_lab_from_image, format_lab_summary
from agents.base_agent import run_consilium, calculate_age
from agents.who_percentiles import format_growth_report
from agents.vaccines_calendar import get_due_vaccines, format_vaccine_report
from services.context_builder import build_profile_context, get_labs_trend

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

# Системный промпт для роутера — Claude понимает намерение пользователя
ROUTER_SYSTEM = """Ты — умный медицинский ассистент семьи. Тебя зовут Доктор Здоров.

Члены семьи:
- Кирилл (папа, 36 лет, взрослый)
- София (дочь, 10 лет)
- Аня (дочь, 7 лет)
- Лука (сын, 3 года)
- Федор (сын, 7 мес.)

Твоя задача: по сообщению пользователя определить НАМЕРЕНИЕ и вернуть JSON.

Возможные намерения:
1. "record_visit" — пользователь рассказывает о визите к врачу
2. "record_lab" — пользователь вводит результаты анализа текстом
3. "record_growth" — рост/вес ребёнка
4. "record_medication" — добавить лекарство
5. "record_vaccine" — прививка
6. "query_labs" — спрашивает про анализы/показатели
7. "query_visits" — спрашивает про визиты к врачам
8. "query_meds" — спрашивает про лекарства
9. "query_growth" — спрашивает про рост/вес/перцентили
10. "query_vaccines" — спрашивает про прививки
11. "consilium" — просит анализ, консультацию по симптому или проблеме
12. "prep_visit" — попросить подготовить к визиту к врачу
13. "general_question" — общий медицинский вопрос
14. "unknown" — непонятно что хочет

Верни ТОЛЬКО JSON без объяснений:
{
  "intent": "одно из намерений выше",
  "person": "имя члена семьи или null если непонятно",
  "details": {
    // для record_visit: "specialty", "doctor", "diagnosis", "prescriptions": [], "recommendations", "follow_up"
    // для record_lab: "test_type", "markers": [{"name", "value", "unit", "ref_min", "ref_max", "status"}]
    // для record_growth: "height_cm", "weight_kg"
    // для record_medication: "name", "dosage", "frequency", "reason", "duration_days"
    // для record_vaccine: "vaccine_name", "date"
    // для query_labs: "marker_name" или null для общего запроса
    // для consilium: "problem"
    // для prep_visit: "specialty"
    // для general_question: "question"
  },
  "confidence": "high|medium|low",
  "response_needed": true/false  // нужно ли уточнить что-то у пользователя
}

ВАЖНО: 
- Если человек не указан явно — поставь null, спросим
- Дозировки и назначения разбирай дотошно
- Если уверенность low — спроси уточнение
- Отвечай всегда на русском в поле user_message если нужно уточнение"""


CHAT_SYSTEM = """Ты — тёплый и профессиональный семейный медицинский ассистент "Доктор Здоров".

Члены семьи:
- Кирилл (папа, 36 лет)
- София (дочь, 10 лет, рождена 28.11.2015)
- Аня (дочь, 7 лет, рождена 04.03.2019)
- Лука (сын, 3 года, рождён 06.04.2023)
- Федор (сын, 7 мес., рождён 12.09.2025)

Правила общения:
- Говори по-русски, тепло и понятно, без медицинского жаргона
- НИКОГДА не ставь диагнозы — только «стоит обсудить с врачом»
- Будь кратким — 3-5 предложений максимум если не просят подробнее
- Подтверждай что сохранил, коротко резюмируй
- Если что-то непонятно — задай ОДИН уточняющий вопрос
- Можно использовать эмодзи умеренно

Контекст из базы данных будет передан ниже."""


def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def get_profile_keyboard(db, exclude_id=None) -> InlineKeyboardMarkup:
    profiles = db.query(Profile).all()
    buttons = []
    row = []
    for p in profiles:
        if p.id == exclude_id:
            continue
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


async def route_message(text: str) -> dict:
    """Claude определяет намерение пользователя."""
    response = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        system=ROUTER_SYSTEM,
        messages=[{"role": "user", "content": text}]
    )
    raw = response.content[0].text
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"intent": "unknown", "person": None, "details": {}, "confidence": "low", "response_needed": True}


async def generate_response(context_text: str, user_message: str, action_done: str = "") -> str:
    """Генерирует тёплый ответ пользователю."""
    system = CHAT_SYSTEM
    if context_text:
        system += f"\n\nДАННЫЕ ИЗ БД:\n{context_text}"

    prompt = user_message
    if action_done:
        prompt = f"Только что выполнено: {action_done}\nСообщение пользователя: {user_message}\nПодтверди кратко что сделано и добавь полезный комментарий."

    response = claude.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


async def handle_record_visit(db, profile: Profile, details: dict, user_msg: str) -> str:
    """Записывает визит к врачу."""
    visit = DoctorVisit(
        profile_id=profile.id,
        date=date.today(),
        specialty=details.get("specialty", ""),
        doctor_name=details.get("doctor", ""),
        diagnosis=details.get("diagnosis", ""),
        prescriptions=details.get("prescriptions", []),
        recommendations=details.get("recommendations", ""),
    )
    follow_up = details.get("follow_up")
    if follow_up:
        visit.follow_up_notes = follow_up

    db.add(visit)

    # Если есть назначения — добавляем как лекарства
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

    action = f"Записан визит для {profile.name}: {details.get('specialty', 'врач')} — {details.get('diagnosis', '')}"
    if details.get("prescriptions"):
        action += f". Назначения: {', '.join(str(p) for p in details.get('prescriptions', []))}"

    return await generate_response("", user_msg, action)


async def handle_record_growth(db, profile: Profile, details: dict, user_msg: str) -> str:
    """Записывает рост и вес."""
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
    report = ""
    if height and weight:
        report = format_growth_report(
            profile.name, age_info["years"], age_info["months"],
            float(height), float(weight), profile.gender or "male"
        )

    action = f"Записан рост/вес для {profile.name}: {height} см, {weight} кг. {report}"
    return await generate_response("", user_msg, action)


async def handle_record_medication(db, profile: Profile, details: dict, user_msg: str) -> str:
    """Добавляет лекарство."""
    med = Medication(
        profile_id=profile.id,
        name=details.get("name", ""),
        dosage=details.get("dosage"),
        frequency=details.get("frequency"),
        reason=details.get("reason"),
        start_date=date.today(),
        is_active=True,
    )

    duration = details.get("duration_days")
    if duration:
        from datetime import timedelta
        med.end_date = date.today() + timedelta(days=int(duration))

    db.add(med)
    db.commit()

    action = f"Добавлено лекарство для {profile.name}: {med.name} {med.dosage or ''} {med.frequency or ''}"
    return await generate_response("", user_msg, action)


async def handle_record_vaccine(db, profile: Profile, details: dict, user_msg: str) -> str:
    """Записывает прививку."""
    vaccine_name = details.get("vaccine_name", "")
    vaccine_date = date.today()

    date_str = details.get("date")
    if date_str:
        try:
            vaccine_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            pass

    v = Vaccine(
        profile_id=profile.id,
        name=vaccine_name,
        date_given=vaccine_date,
        is_completed=True,
    )
    db.add(v)
    db.commit()

    action = f"Записана прививка для {profile.name}: {vaccine_name}"
    return await generate_response("", user_msg, action)


async def handle_query_labs(db, profile: Profile, details: dict, user_msg: str) -> str:
    """Отвечает на вопрос про анализы."""
    marker_name = details.get("marker_name")

    if marker_name:
        trend = get_labs_trend(db, profile.id, marker_name)
        if trend:
            lines = [f"📈 {marker_name} — {profile.name}\n"]
            for point in trend[-8:]:
                icon = "✅" if point["status"] == "normal" else ("🔴" if "critical" in str(point["status"]) else "🟡")
                ref = ""
                if point.get("ref_min") and point.get("ref_max"):
                    ref = f" (норма {point['ref_min']}–{point['ref_max']})"
                lines.append(f"{icon} {point['date']}: {point['value']} {point.get('unit', '')}{ref}")
            return "\n".join(lines)
        else:
            return f"По показателю «{marker_name}» для {profile.name} данных пока нет. Скинь фото анализа — сохраню."
    else:
        # Показываем последние анализы
        labs = db.query(LabResult).filter(
            LabResult.profile_id == profile.id
        ).order_by(LabResult.date.desc()).limit(5).all()

        if not labs:
            return f"Для {profile.name} анализов пока нет. Сфотографируй бланк и скинь сюда — я всё распознаю и сохраню."

        context_str = build_profile_context(db, profile, limit_labs=5)
        return await generate_response(context_str, user_msg)


async def handle_consilium(db, profile: Profile, details: dict, user_msg: str) -> str:
    """Запускает мультиагентный консилиум."""
    problem = details.get("problem", user_msg)
    context_str = build_profile_context(db, profile)

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

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_consilium, profile_dict, context_str, problem)
    return result


async def handle_general_question(db, profile: Optional[Profile], user_msg: str) -> str:
    """Отвечает на общий медицинский вопрос."""
    context_str = ""
    if profile:
        context_str = build_profile_context(db, profile, limit_labs=5, limit_visits=5)

    return await generate_response(context_str, user_msg)


# ====== MAIN HANDLERS ======

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик всех текстовых сообщений."""
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS:
        return

    text = update.message.text.strip()
    db = get_db()

    try:
        # Показываем что думаем
        thinking_msg = await update.message.reply_text("⏳")

        # Роутер определяет намерение
        loop = asyncio.get_event_loop()
        routed = await loop.run_in_executor(None, lambda: asyncio.run(route_message(text)))

        # Находим профиль
        profile = None
        person_name = routed.get("person")
        if person_name:
            profile = find_profile(db, person_name)

        intent = routed.get("intent", "unknown")
        details = routed.get("details", {})
        confidence = routed.get("confidence", "low")

        # Если человек не определён и нужен — спрашиваем
        intents_needing_person = {
            "record_visit", "record_lab", "record_growth",
            "record_medication", "record_vaccine",
            "query_labs", "query_visits", "query_growth",
            "query_vaccines", "query_meds", "consilium", "prep_visit"
        }

        if intent in intents_needing_person and not profile:
            # Сохраняем pending action
            context.user_data["pending_intent"] = routed
            context.user_data["pending_text"] = text

            await thinking_msg.edit_text(
                "Для кого это?",
                reply_markup=get_profile_keyboard(db)
            )
            db.close()
            return

        # Выполняем действие
        response = ""

        if intent == "record_visit" and profile:
            response = await handle_record_visit(db, profile, details, text)

        elif intent == "record_growth" and profile:
            response = await handle_record_growth(db, profile, details, text)

        elif intent == "record_medication" and profile:
            response = await handle_record_medication(db, profile, details, text)

        elif intent == "record_vaccine" and profile:
            response = await handle_record_vaccine(db, profile, details, text)

        elif intent == "query_labs" and profile:
            response = await handle_query_labs(db, profile, details, text)

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
                lines = [report, "\nИстория:"]
                for r in records:
                    lines.append(f"• {r.date.strftime('%d.%m.%Y')}: {r.height_cm} см, {r.weight_kg} кг")
                response = "\n".join(lines)
            else:
                response = f"Данных по росту/весу для {profile.name} пока нет. Напиши что-то вроде «Лука 95 см, 14.5 кг»"

        elif intent == "query_vaccines" and profile:
            vaccines_raw = db.query(Vaccine).filter(Vaccine.profile_id == profile.id).all()
            vaccines_list = [{"name": v.name, "date_given": v.date_given, "is_completed": v.is_completed} for v in vaccines_raw]
            vaccine_data = get_due_vaccines(profile.birthdate, vaccines_list)
            response = format_vaccine_report(profile.name, vaccine_data)

        elif intent == "query_meds" and profile:
            active = db.query(Medication).filter(
                Medication.profile_id == profile.id,
                Medication.is_active == True
            ).all()
            if active:
                lines = [f"💊 Текущие лекарства — {profile.name}\n"]
                for m in active:
                    end = f" до {m.end_date.strftime('%d.%m')}" if m.end_date else ""
                    lines.append(f"• {m.name} {m.dosage or ''} {m.frequency or ''}{end}")
                    if m.reason:
                        lines.append(f"  ({m.reason})")
                response = "\n".join(lines)
            else:
                response = f"У {profile.name} сейчас нет активных лекарств."

        elif intent == "query_visits" and profile:
            visits = db.query(DoctorVisit).filter(
                DoctorVisit.profile_id == profile.id
            ).order_by(DoctorVisit.date.desc()).limit(5).all()
            if visits:
                context_str = build_profile_context(db, profile, limit_labs=0, limit_visits=5)
                response = await generate_response(context_str, text)
            else:
                response = f"Визитов для {profile.name} пока нет."

        elif intent == "consilium" and profile:
            await thinking_msg.edit_text(
                f"🔄 Запускаю анализ для {profile.name}...\n"
                "Это займёт около минуты — работают несколько специалистов параллельно."
            )
            response = await handle_consilium(db, profile, details, text)

        elif intent == "prep_visit" and profile:
            specialty = details.get("specialty", "врача")
            await thinking_msg.edit_text(f"⏳ Готовлю чеклист к {specialty}...")
            context_str = build_profile_context(db, profile)
            age_info = calculate_age(profile.birthdate)

            prep_response = claude.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": f"""Подготовь чеклист к {specialty} для {profile.name}, {age_info['years']} лет.

ДАННЫЕ:
{context_str}

Составь на русском:
1. **Что взять с собой**
2. **Что рассказать врачу** (на основе истории)
3. **Что спросить у врача**
4. **Какие анализы обсудить** (если есть отклонения)

Кратко, по делу, без лишнего."""
                }]
            )
            response = f"📋 Чеклист к {specialty} — {profile.name}\n\n{prep_response.content[0].text}"

        else:
            # general_question или unknown
            response = await handle_general_question(db, profile, text)

        # Удаляем "думающее" сообщение и отвечаем
        await thinking_msg.delete()

        # Разбиваем длинные ответы
        MAX = 4000
        if len(response) <= MAX:
            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            for i, chunk in enumerate(response[i:i+MAX] for i in range(0, len(response), MAX)):
                await update.message.reply_text(chunk, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        try:
            await thinking_msg.edit_text("Что-то пошло не так. Попробуй ещё раз или перефразируй.")
        except Exception:
            await update.message.reply_text("Что-то пошло не так. Попробуй ещё раз.")
    finally:
        db.close()


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает фото анализа."""
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS:
        return

    caption = update.message.caption or ""
    db = get_db()
    try:
        # Пробуем определить профиль из подписи
        profile = None
        if caption:
            words = caption.split()
            if words:
                profile = find_profile(db, words[0])

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
    """Обрабатывает PDF и изображения как документы."""
    if ALLOWED_USER_IDS and update.effective_user.id not in ALLOWED_USER_IDS:
        return

    doc = update.message.document
    allowed_types = ("image/jpeg", "image/png", "image/webp", "application/pdf")
    if doc.mime_type not in allowed_types:
        await update.message.reply_text("Поддерживаю: JPG, PNG, PDF, WebP")
        return

    caption = update.message.caption or ""
    db = get_db()
    try:
        profile = None
        if caption:
            profile = find_profile(db, caption.split()[0])

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
    """Распознаёт анализ из фото и сохраняет."""
    try:
        msg = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query
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
        await thinking.edit_text(f"✅ Сохранено!\n\n{summary}", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Lab photo error: {e}")
        await thinking.edit_text("Не смог распознать анализ. Попробуй более чёткое фото.")


async def _process_lab_document(update_or_query, context, db, profile, file_id, mime_type):
    """Распознаёт анализ из документа/PDF."""
    try:
        msg = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query
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
        await thinking.edit_text(f"✅ Сохранено!\n\n{summary}", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Lab doc error: {e}")
        await thinking.edit_text("Не смог обработать документ. Попробуй ещё раз.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок (выбор профиля)."""
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

        # Есть ожидающее фото?
        if "pending_lab_photo" in context.user_data:
            file_id = context.user_data.pop("pending_lab_photo")
            await query.edit_message_text(f"Обрабатываю анализ для {profile.name}...")
            await _process_lab_photo(query, context, db, profile, file_id)
            return

        if "pending_lab_doc" in context.user_data:
            file_id = context.user_data.pop("pending_lab_doc")
            mime_type = context.user_data.pop("pending_lab_mime", "image/jpeg")
            await query.edit_message_text(f"Обрабатываю документ для {profile.name}...")
            await _process_lab_document(query, context, db, profile, file_id, mime_type)
            return

        # Есть ожидающее намерение?
        if "pending_intent" in context.user_data:
            routed = context.user_data.pop("pending_intent")
            original_text = context.user_data.pop("pending_text", "")
            routed["person"] = profile.name

            await query.edit_message_text(f"Понял, это для {profile.name}. Обрабатываю...")

            # Повторно выполняем с известным профилем
            intent = routed.get("intent", "unknown")
            details = routed.get("details", {})

            response = ""
            if intent == "record_visit":
                response = await handle_record_visit(db, profile, details, original_text)
            elif intent == "record_growth":
                response = await handle_record_growth(db, profile, details, original_text)
            elif intent == "record_medication":
                response = await handle_record_medication(db, profile, details, original_text)
            elif intent == "record_vaccine":
                response = await handle_record_vaccine(db, profile, details, original_text)
            elif intent == "query_labs":
                response = await handle_query_labs(db, profile, details, original_text)
            elif intent == "consilium":
                response = await handle_consilium(db, profile, details, original_text)
            else:
                response = await handle_general_question(db, profile, original_text)

            await query.message.reply_text(response, parse_mode="Markdown")
            return

        # Просто показываем профиль
        age_info = calculate_age(profile.birthdate)
        await query.edit_message_text(
            f"Выбран: **{profile.name}**, {age_info['years']} лет\n"
            "Теперь пиши — я всё пойму 👍",
            parse_mode="Markdown"
        )
    finally:
        db.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие."""
    await update.message.reply_text(
        "Привет! Я Доктор Здоров 🏥\n\n"
        "Просто пиши мне как другу:\n\n"
        "• _«Аня была у лора, поставили тонзиллит»_\n"
        "• _«Лука 95 см, 14 кг»_\n"
        "• _«Покажи анализы крови Кирилла»_\n"
        "• _«Когда Феде делали прививки?»_\n"
        "• Или просто скинь фото анализа — всё распознаю\n\n"
        "Я сам пойму что нужно сделать 👌",
        parse_mode="Markdown"
    )


def main():
    create_tables()

    try:
        from models.profiles_seed import seed_profiles
        seed_profiles()
    except Exception as e:
        logger.warning(f"Seed: {e}")

    app = Application.builder().token(TG_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Health-OS Bot v2 запущен — свободный чат")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
