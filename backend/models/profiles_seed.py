"""
Начальные профили семьи.
Запускается при каждом старте — добавляет только отсутствующих.
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
        "notes": "Взрослый профиль. CEO/основатель.",
    },
    {
        "name": "Маша",
        "birthdate": date(1987, 1, 21),
        "gender": "female",
        "blood_type": None,
        "is_child": False,
        "allergies": [],
        "chronic_conditions": [],
        "family_history": {},
        "notes": "Мама.",
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
        # Удаляем устаревший профиль "Мама" если есть
        old = db.query(Profile).filter(Profile.name == "Мама").all()
        for o in old:
            db.delete(o)
        if old:
            db.commit()
            print(f"Удалён устаревший профиль Мама")
        # Добавляем только отсутствующих
        added = 0
        for p in FAMILY_PROFILES:
            if p["name"] not in existing_names:
                db.add(Profile(**p))
                added += 1
        if added:
            db.commit()
            print(f"Добавлено {added} новых профилей")
        else:
            print(f"Все профили актуальны ({len(existing_names)} в БД)")
    finally:
        db.close()


if __name__ == "__main__":
    seed_profiles()

