"""
Национальный календарь прививок РФ 2024.
Проверяет статус вакцинации ребёнка по возрасту.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional

# Нацкалендарь РФ — ключевые прививки по возрасту
VACCINATION_SCHEDULE = [
    {"age_months": 0, "name": "Гепатит B (1-я доза)", "id": "hepb_1"},
    {"age_months": 0, "name": "БЦЖ (туберкулёз)", "id": "bcg_1"},
    {"age_months": 1, "name": "Гепатит B (2-я доза)", "id": "hepb_2"},
    {"age_months": 2, "name": "АКДС/пентаксим (1-я доза)", "id": "dtp_1"},
    {"age_months": 2, "name": "Полиомиелит ИПВ (1-я доза)", "id": "ipv_1"},
    {"age_months": 2, "name": "Пневмококк (1-я доза)", "id": "pcv_1"},
    {"age_months": 2, "name": "Гемофильная инфекция Hib (1-я доза)", "id": "hib_1"},
    {"age_months": 3, "name": "АКДС/пентаксим (2-я доза)", "id": "dtp_2"},
    {"age_months": 3, "name": "Полиомиелит ИПВ (2-я доза)", "id": "ipv_2"},
    {"age_months": 3, "name": "Гемофильная инфекция Hib (2-я доза)", "id": "hib_2"},
    {"age_months": 4, "name": "АКДС/пентаксим (3-я доза)", "id": "dtp_3"},
    {"age_months": 4, "name": "Полиомиелит ОПВ (3-я доза)", "id": "opv_3"},
    {"age_months": 4, "name": "Пневмококк (2-я доза)", "id": "pcv_2"},
    {"age_months": 4, "name": "Гемофильная инфекция Hib (3-я доза)", "id": "hib_3"},
    {"age_months": 6, "name": "Гепатит B (3-я доза)", "id": "hepb_3"},
    {"age_months": 12, "name": "КПК (корь, паротит, краснуха, 1-я доза)", "id": "mmr_1"},
    {"age_months": 12, "name": "Ветряная оспа (1-я доза)", "id": "varicella_1"},
    {"age_months": 12, "name": "Пневмококк (ревакцинация)", "id": "pcv_r"},
    {"age_months": 18, "name": "АКДС/пентаксим (ревакцинация 1-я)", "id": "dtp_r1"},
    {"age_months": 18, "name": "Полиомиелит ОПВ (ревакцинация 1-я)", "id": "opv_r1"},
    {"age_months": 18, "name": "Гемофильная инфекция Hib (ревакцинация)", "id": "hib_r"},
    {"age_months": 20, "name": "Полиомиелит ОПВ (ревакцинация 2-я)", "id": "opv_r2"},
    {"age_months": 72, "name": "КПК (ревакцинация)", "id": "mmr_2"},
    {"age_months": 72, "name": "АДС-М (ревакцинация)", "id": "dt_r"},
    {"age_months": 72, "name": "Полиомиелит ОПВ (ревакцинация 3-я)", "id": "opv_r3"},
    {"age_months": 84, "name": "Ветряная оспа (2-я доза, если не болел)", "id": "varicella_2"},
    {"age_months": 132, "name": "Краснуха (девочки, доп. доза)", "id": "rubella_girls"},
    {"age_months": 132, "name": "Гепатит B (если не привит ранее)", "id": "hepb_catch"},
    {"age_months": 168, "name": "АДС-М (ревакцинация)", "id": "dt_r2"},
]


def get_due_vaccines(birthdate: date, given_vaccines: List[Dict]) -> Dict:
    """
    Возвращает статус вакцинации.
    given_vaccines: список из БД [{name, date_given, is_completed}]
    """
    today = date.today()
    age_months = (today.year - birthdate.year) * 12 + (today.month - birthdate.month)

    given_names = {v["name"].lower() for v in given_vaccines if v.get("is_completed")}

    overdue = []
    upcoming = []
    done = []

    for vaccine in VACCINATION_SCHEDULE:
        if vaccine["age_months"] > age_months + 6:
            continue  # Слишком далеко в будущем

        # Проверяем, сделана ли прививка (по частичному совпадению имени)
        is_done = any(vaccine["name"].lower()[:15] in g for g in given_names)

        due_date = date(birthdate.year, birthdate.month, 1) + timedelta(days=vaccine["age_months"] * 30)

        if is_done:
            done.append(vaccine["name"])
        elif vaccine["age_months"] <= age_months:
            overdue.append({
                "name": vaccine["name"],
                "was_due_at": f"{vaccine['age_months']} мес.",
                "delay_months": age_months - vaccine["age_months"]
            })
        elif vaccine["age_months"] <= age_months + 6:
            upcoming.append({
                "name": vaccine["name"],
                "due_at": f"{vaccine['age_months']} мес.",
                "approx_date": due_date.strftime("%m.%Y")
            })

    return {
        "done_count": len(done),
        "overdue": overdue,
        "upcoming": upcoming,
    }


def format_vaccine_report(name: str, vaccine_data: Dict) -> str:
    """Форматирует отчёт по вакцинации для Telegram."""
    lines = [f"💉 **Прививки — {name}**", ""]

    if vaccine_data["overdue"]:
        lines.append(f"🔴 **Просрочено ({len(vaccine_data['overdue'])}):**")
        for v in vaccine_data["overdue"]:
            lines.append(f"  • {v['name']} (должна была быть в {v['was_due_at']}, просрочка {v['delay_months']} мес.)")
        lines.append("")

    if vaccine_data["upcoming"]:
        lines.append(f"📅 **Предстоят (ближайшие 6 мес.):**")
        for v in vaccine_data["upcoming"]:
            lines.append(f"  • {v['name']} — к {v['approx_date']}")
        lines.append("")

    lines.append(f"✅ Сделано (из известных): {vaccine_data['done_count']}")

    if not vaccine_data["overdue"] and not vaccine_data["upcoming"]:
        lines.append("\n🎉 Все актуальные прививки сделаны!")

    return "\n".join(lines)
