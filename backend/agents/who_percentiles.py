"""
Расчёт перцентилей роста и веса по таблицам ВОЗ (упрощённая версия).
Используется для детских профилей.
"""
import math
from typing import Optional, Tuple

# ВОЗ LMS параметры для роста мальчиков (0-24 месяца) — ключевые точки
# L (Box-Cox power), M (median), S (coefficient of variation)
# Источник: WHO Child Growth Standards
WHO_HEIGHT_BOYS_0_24 = {
    0: (1, 49.9, 0.03795),
    3: (1, 61.4, 0.03564),
    6: (1, 67.6, 0.03497),
    9: (1, 72.3, 0.03530),
    12: (1, 75.7, 0.03560),
    18: (1, 82.3, 0.03680),
    24: (1, 87.8, 0.03765),
}

WHO_HEIGHT_GIRLS_0_24 = {
    0: (1, 49.1, 0.03790),
    3: (1, 59.8, 0.03640),
    6: (1, 65.7, 0.03568),
    9: (1, 70.1, 0.03585),
    12: (1, 74.0, 0.03619),
    18: (1, 80.7, 0.03768),
    24: (1, 86.4, 0.03875),
}

# Приближённые референсы для подростков (упрощённо, P5-P95)
CHILD_HEIGHT_REFS = {
    "male": {
        2: (82, 92), 3: (88, 100), 4: (96, 108), 5: (103, 115),
        6: (109, 121), 7: (115, 127), 8: (121, 134), 9: (127, 140),
        10: (132, 146), 11: (137, 153), 12: (143, 161), 13: (150, 170),
        14: (157, 177), 15: (163, 181), 16: (165, 183), 17: (167, 185),
    },
    "female": {
        2: (80, 91), 3: (87, 99), 4: (94, 107), 5: (101, 114),
        6: (107, 120), 7: (113, 127), 8: (119, 133), 9: (124, 140),
        10: (129, 145), 11: (134, 151), 12: (140, 158), 13: (145, 162),
        14: (148, 165), 15: (150, 166), 16: (151, 167), 17: (152, 168),
    }
}

CHILD_WEIGHT_REFS = {
    "male": {
        2: (10.5, 14.5), 3: (12.0, 17.0), 4: (13.5, 19.5), 5: (15.0, 22.0),
        6: (16.5, 24.5), 7: (18.5, 28.0), 8: (20.0, 32.0), 9: (22.5, 36.0),
        10: (24.5, 41.0), 11: (27.0, 47.0), 12: (30.0, 55.0), 13: (33.0, 62.0),
        14: (37.0, 70.0), 15: (41.0, 76.0), 16: (44.0, 80.0), 17: (47.0, 83.0),
    },
    "female": {
        2: (9.8, 14.2), 3: (11.5, 16.5), 4: (12.8, 19.0), 5: (14.5, 22.0),
        6: (16.0, 25.0), 7: (17.5, 28.5), 8: (19.5, 33.0), 9: (21.5, 38.0),
        10: (24.0, 44.0), 11: (26.5, 50.0), 12: (30.0, 57.0), 13: (33.0, 62.0),
        14: (36.0, 65.0), 15: (38.0, 67.0), 16: (39.5, 68.0), 17: (40.5, 69.0),
    }
}


def estimate_percentile(value: float, p5: float, p50: float, p95: float) -> float:
    """Приближённый расчёт перцентиля через нормальное распределение."""
    from scipy.stats import norm
    try:
        sd = (p95 - p5) / (2 * 1.645)
        z = (value - p50) / sd
        return round(norm.cdf(z) * 100, 1)
    except Exception:
        # Без scipy — линейная интерполяция
        if value <= p5:
            return 5.0
        elif value >= p95:
            return 95.0
        elif value <= p50:
            return 5 + (value - p5) / (p50 - p5) * 45
        else:
            return 50 + (value - p50) / (p95 - p50) * 45


def get_height_percentile(age_years: int, height_cm: float, gender: str) -> Optional[Tuple[float, str]]:
    """Возвращает (перцентиль, оценка) для роста."""
    refs = CHILD_HEIGHT_REFS.get(gender, CHILD_HEIGHT_REFS["male"])
    age_key = min(refs.keys(), key=lambda x: abs(x - age_years))
    p5, p95 = refs[age_key]
    p50 = (p5 + p95) / 2

    percentile = estimate_percentile(height_cm, p5, p50, p95)
    assessment = _assess_percentile(percentile)
    return percentile, assessment


def get_weight_percentile(age_years: int, weight_kg: float, gender: str) -> Optional[Tuple[float, str]]:
    """Возвращает (перцентиль, оценка) для веса."""
    refs = CHILD_WEIGHT_REFS.get(gender, CHILD_WEIGHT_REFS["male"])
    age_key = min(refs.keys(), key=lambda x: abs(x - age_years))
    p5, p95 = refs[age_key]
    p50 = (p5 + p95) / 2

    percentile = estimate_percentile(weight_kg, p5, p50, p95)
    assessment = _assess_percentile(percentile)
    return percentile, assessment


def _assess_percentile(p: float) -> str:
    if p < 3:
        return "🔴 Очень низкий (<P3)"
    elif p < 10:
        return "🟡 Низкий (P3-P10)"
    elif p < 25:
        return "🟢 Ниже среднего (P10-P25)"
    elif p < 75:
        return "✅ Средний (P25-P75)"
    elif p < 90:
        return "🟢 Выше среднего (P75-P90)"
    elif p < 97:
        return "🟡 Высокий (P90-P97)"
    else:
        return "🔴 Очень высокий (>P97)"


def format_growth_report(name: str, age_years: int, age_months: int,
                          height_cm: Optional[float], weight_kg: Optional[float],
                          gender: str = "male") -> str:
    """Форматирует отчёт по росту/весу для Telegram."""
    lines = [f"📏 **Рост и вес — {name}**",
             f"Возраст: {age_years} лет {age_months} мес."]

    if height_cm:
        result = get_height_percentile(age_years, height_cm, gender)
        if result:
            p, assessment = result
            lines.append(f"📐 Рост: {height_cm} см — {assessment} (P{p})")

    if weight_kg:
        result = get_weight_percentile(age_years, weight_kg, gender)
        if result:
            p, assessment = result
            lines.append(f"⚖️ Вес: {weight_kg} кг — {assessment} (P{p})")

    if height_cm and weight_kg:
        bmi = weight_kg / ((height_cm / 100) ** 2)
        lines.append(f"📊 ИМТ: {bmi:.1f}")

    return "\n".join(lines)
