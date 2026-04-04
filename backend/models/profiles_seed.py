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
        existing = db.query(Profile).count()
        if existing == 0:
            for p in FAMILY_PROFILES:
                profile = Profile(**p)
                db.add(profile)
            db.commit()
            print(f"Созданы {len(FAMILY_PROFILES)} профилей семьи")
        else:
            print(f"Профили уже существуют ({existing} штук)")
    finally:
        db.close()


if __name__ == "__main__":
    seed_profiles()
