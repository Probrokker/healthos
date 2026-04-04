"""
Собирает полный медицинский контекст профиля из БД для передачи агентам.
"""
from datetime import date, datetime
from sqlalchemy.orm import Session
from models.database import Profile, LabResult, DoctorVisit, Medication, GrowthRecord, Vaccine, Hypothesis
import json


def build_profile_context(db: Session, profile: Profile, limit_labs: int = 10, limit_visits: int = 10) -> str:
    """Строит текстовый контекст профиля для AI-агентов."""
    today = date.today()
    age_years = today.year - profile.birthdate.year - (
        (today.month, today.day) < (profile.birthdate.month, profile.birthdate.day)
    )

    lines = [
        f"=== МЕДИЦИНСКИЙ ПРОФИЛЬ: {profile.name} ===",
        f"Возраст: {age_years} лет (ДР: {profile.birthdate.strftime('%d.%m.%Y')})",
        f"Пол: {profile.gender or 'не указан'}",
        f"Группа крови: {profile.blood_type or 'не указана'}",
        f"Аллергии: {', '.join(profile.allergies) if profile.allergies else 'нет данных'}",
        f"Хронические состояния: {', '.join(profile.chronic_conditions) if profile.chronic_conditions else 'нет'}",
    ]

    if profile.family_history:
        lines.append(f"Семейный анамнез: {json.dumps(profile.family_history, ensure_ascii=False)}")

    if profile.notes:
        lines.append(f"Заметки: {profile.notes}")

    # Активные медикаменты
    active_meds = db.query(Medication).filter(
        Medication.profile_id == profile.id,
        Medication.is_active == True
    ).all()

    if active_meds:
        lines.append("\n--- ТЕКУЩИЕ ЛЕКАРСТВА ---")
        for med in active_meds:
            lines.append(f"• {med.name} {med.dosage or ''} {med.frequency or ''} — {med.reason or ''}")

    # Последние анализы
    labs = db.query(LabResult).filter(
        LabResult.profile_id == profile.id
    ).order_by(LabResult.date.desc()).limit(limit_labs).all()

    if labs:
        lines.append("\n--- ПОСЛЕДНИЕ АНАЛИЗЫ ---")
        for lab in labs:
            lines.append(f"\n📋 {lab.test_type} от {lab.date.strftime('%d.%m.%Y')} ({lab.lab_name or 'лаборатория'})")
            if lab.markers:
                for marker in lab.markers:
                    status_icon = ""
                    if marker.get("status") == "high":
                        status_icon = " ↑"
                    elif marker.get("status") == "low":
                        status_icon = " ↓"
                    elif "critical" in str(marker.get("status", "")):
                        status_icon = " ❗"
                    ref = ""
                    if marker.get("ref_min") and marker.get("ref_max"):
                        ref = f" (норма: {marker['ref_min']}–{marker['ref_max']})"
                    lines.append(
                        f"  {marker.get('name', '?')}: {marker.get('value', '?')} {marker.get('unit', '')}{status_icon}{ref}"
                    )

    # Последние визиты
    visits = db.query(DoctorVisit).filter(
        DoctorVisit.profile_id == profile.id
    ).order_by(DoctorVisit.date.desc()).limit(limit_visits).all()

    if visits:
        lines.append("\n--- ПОСЛЕДНИЕ ВИЗИТЫ К ВРАЧАМ ---")
        for visit in visits:
            lines.append(f"\n👨‍⚕️ {visit.specialty or 'Врач'} {visit.doctor_name or ''} — {visit.date.strftime('%d.%m.%Y')}")
            if visit.diagnosis:
                lines.append(f"  Диагноз: {visit.diagnosis}")
            if visit.prescriptions:
                lines.append(f"  Назначения: {json.dumps(visit.prescriptions, ensure_ascii=False)}")
            if visit.recommendations:
                lines.append(f"  Рекомендации: {visit.recommendations}")

    # Последние данные роста
    growth = db.query(GrowthRecord).filter(
        GrowthRecord.profile_id == profile.id
    ).order_by(GrowthRecord.date.desc()).limit(3).all()

    if growth:
        lines.append("\n--- РОСТ И ВЕС ---")
        for g in growth:
            lines.append(f"  {g.date.strftime('%d.%m.%Y')}: рост {g.height_cm or '?'} см, вес {g.weight_kg or '?'} кг")

    # Гипотезы
    hypotheses = db.query(Hypothesis).filter(
        Hypothesis.profile_id == profile.id,
        Hypothesis.status.notin_(["refuted", "confirmed"])
    ).all()

    if hypotheses:
        lines.append("\n--- АКТИВНЫЕ ГИПОТЕЗЫ ---")
        for h in hypotheses:
            lines.append(f"  [{h.status.upper()}] {h.title}")
            if h.next_steps:
                lines.append(f"  Следующие шаги: {', '.join(h.next_steps)}")

    return "\n".join(lines)


def get_labs_trend(db: Session, profile_id: int, marker_name: str, limit: int = 20) -> list:
    """Возвращает тренд конкретного показателя."""
    labs = db.query(LabResult).filter(
        LabResult.profile_id == profile_id
    ).order_by(LabResult.date.asc()).limit(50).all()

    trend = []
    for lab in labs:
        for marker in (lab.markers or []):
            if marker_name.lower() in marker.get("name", "").lower():
                try:
                    value = float(str(marker["value"]).replace(",", "."))
                    trend.append({
                        "date": lab.date.isoformat(),
                        "value": value,
                        "unit": marker.get("unit", ""),
                        "status": marker.get("status", "normal"),
                        "ref_min": marker.get("ref_min"),
                        "ref_max": marker.get("ref_max"),
                    })
                except (ValueError, TypeError):
                    pass

    return trend[-limit:]
