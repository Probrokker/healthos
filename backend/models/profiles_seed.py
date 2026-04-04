"""
Начальные профили семьи Кирилла.
Запускается один раз при инициализации БД.
"""
from datetime import date
from database import SessionLocal, Profile, create_tables

FAMILY_PROFILES = [
    {
        "name": "Кирилл",
        "birthdate": date(1989, 9, 14),
        "gender": "male",
        "blood_type": None,
        "is_child": False,
        "allergies": [],
        "chronic_conditions": [],
        "family_history": {},
        "notes": "Взрослый профиль. CEO/основатель. Бизнес-нагрузка, командировки, адаптогены.",
    },
    {
        "name": "Мама",
        "birthdate": date(1987, 1, 21),
        "gender": "female",
        "blood_type": None,
        "is_child": False,
        "allergies": [],
        "chronic_conditions": [],
        "family_history": {},
        "notes": "Взрослый профиль. 39 лет.",
    },
    {
        "name": "София",
        "birthdate": date(2015, 11, 28),
        "gender": "female",
        "blood_type": None,
        "is_child": True,
        "allergies": [],
        "chronic_conditions": [],
        "family_history": {},
        "notes": "Дочь. 10 лет.",
    },
    {
        "name": "Аня",
        "birthdate": date(2019, 3, 4),
        "gender": "female",
        "blood_type": None,
        "is_child": True,
        "allergies": [],
        "chronic_conditions": [],
        "family_history": {},
        "notes": "Дочь. 7 лет.",
    },
    {
        "name": "Лука",
        "birthdate": date(2023, 4, 6),
        "gender": "male",
        "blood_type": None,
        "is_child": True,
        "allergies": [],
        "chronic_conditions": [],
        "family_history": {},
        "notes": "Сын. 3 года.",
    },
    {
        "name": "Федор",
        "birthdate": date(2025, 9, 12),
        "gender": "male",
        "blood_type": None,
        "is_child": True,
        "allergies": [],
        "chronic_conditions": [],
        "family_history": {},
        "notes": "Сын. Младенец.",
    },
]


def seed_profiles():
    create_tables()
    db = SessionLocal()
    try:
        existing_names = {p.name for p in db.query(Profile).all()}
        added = 0
        for p in FAMILY_PROFILES:
            if p["name"] not in existing_names:
                profile = Profile(**p)
                db.add(profile)
                added += 1
        db.commit()
        if added:
            print(f"Добавлено {added} новых профилей")
        else:
            print(f"Все профили уже существуют ({len(existing_names)} штук)")
    finally:
        db.close()


if __name__ == "__main__":
    seed_profiles()

