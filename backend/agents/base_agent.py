"""
Базовый класс AI-агента. Все специализированные агенты наследуются отсюда.
"""
import anthropic
import os
from datetime import date, datetime
from typing import Optional

client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

ADULT_SPECIALISTS = [
    {
        "id": "cardiologist",
        "name": "Кардиолог",
        "focus": "Сердечно-сосудистая система",
        "prompt": """Ты — опытный кардиолог. Анализируй данные строго с точки зрения сердечно-сосудистой системы.
Смотри на: АД, ЧСС, холестерин (общий, ЛПНП, ЛПВП, триглицериды), ЭКГ-данные, СРБ, гомоцистеин.
Учитывай: высокую бизнес-нагрузку, командировки, стресс, адаптогены.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с врачом»."""
    },
    {
        "id": "endocrinologist",
        "name": "Эндокринолог",
        "focus": "Гормоны и метаболизм",
        "prompt": """Ты — опытный эндокринолог. Анализируй гормональный профиль и метаболизм.
Смотри на: ТТГ, Т4 свободный, тестостерон, кортизол, инсулин, глюкоза, HbA1c, ДГЭА-С, ЛГ, ФСГ.
Учитывай: возраст 36 лет, стресс, нагрузки, приём адаптогенов.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с врачом»."""
    },
    {
        "id": "hematologist",
        "name": "Гематолог",
        "focus": "Кровь",
        "prompt": """Ты — опытный гематолог. Анализируй показатели крови.
Смотри на: ОАК (Hb, эритроциты, лейкоциты, тромбоциты, лейкоформула), ферритин, железо, витамин B12, фолиевая кислота.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с врачом»."""
    },
    {
        "id": "gastroenterologist",
        "name": "Гастроэнтеролог",
        "focus": "ЖКТ и печень",
        "prompt": """Ты — опытный гастроэнтеролог. Анализируй показатели ЖКТ и печени.
Смотри на: АЛТ, АСТ, билирубин, щелочная фосфатаза, ГГТ, альбумин, H.pylori, копрограмма.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с врачом»."""
    },
    {
        "id": "neurologist",
        "name": "Невролог",
        "focus": "Нервная система",
        "prompt": """Ты — опытный невролог. Анализируй нервную систему и когнитивную функцию.
Смотри на: витамин D, B12, магний, ЭЭГ-данные, сон, усталость, головные боли, HRV.
Учитывай: бизнес-нагрузку, нерегулярный сон, стресс.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с врачом»."""
    },
    {
        "id": "nutritionist",
        "name": "Нутрициолог",
        "focus": "Питание и добавки",
        "prompt": """Ты — опытный нутрициолог и специалист по спортивной медицине.
Смотри на: нутриентный статус, баланс макро/микроэлементов, дефициты витаминов.
Учитывай: приём адаптогенов (если указаны), командировки, нерегулярное питание.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с врачом»."""
    },
]

CHILD_SPECIALISTS = [
    {
        "id": "pediatrician",
        "name": "Педиатр",
        "focus": "Общее развитие",
        "prompt": """Ты — опытный педиатр. Оценивай общее физическое и психомоторное развитие ребёнка.
Смотри на: перцентили роста/веса по ВОЗ, частоту ОРВИ, паттерны заболеваний, нацкалендарь прививок РФ.
Все нормы — ПЕДИАТРИЧЕСКИЕ, учитывай возраст ребёнка в годах и месяцах.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с педиатром»."""
    },
    {
        "id": "hematologist_child",
        "name": "Гематолог (дет.)",
        "focus": "Кровь (детские нормы)",
        "prompt": """Ты — детский гематолог. Оценивай показатели крови по ДЕТСКИМ референсным значениям.
Смотри на: ОАК (Hb, эритроциты, лейкоциты, тромбоциты, лейкоформула), ферритин, железо.
ВАЖНО: детские нормы отличаются от взрослых — всегда используй возрастные референсы.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с педиатром»."""
    },
    {
        "id": "allergologist",
        "name": "Аллерголог",
        "focus": "Аллергии",
        "prompt": """Ты — детский аллерголог-иммунолог.
Смотри на: общий и специфические IgE, эозинофилы, кожные пробы, паттерны реакций, триггеры.
Отслеживай сезонность и связь с питанием.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с аллергологом»."""
    },
    {
        "id": "ent",
        "name": "ЛОР",
        "focus": "Ухо-горло-нос",
        "prompt": """Ты — детский ЛОР (оториноларинголог).
Смотри на: частоту ангин, отитов, ОРВИ, аденоиды, хронические процессы.
Обращай внимание на паттерны (>6 ОРВИ в год = сигнал).
НИКОГДА не ставь диагнозы. Только «стоит обсудить с ЛОРом»."""
    },
    {
        "id": "dentist",
        "name": "Стоматолог",
        "focus": "Зубы",
        "prompt": """Ты — детский стоматолог.
Смотри на: кариес молочных/постоянных зубов, прикус, сроки смены зубов, брекеты.
Учитывай возраст: у детей до 6-7 лет молочные зубы, потом смена.
НИКОГДА не ставь диагнозы. Только «стоит обсудить со стоматологом»."""
    },
    {
        "id": "orthopedist",
        "name": "Ортопед",
        "focus": "Осанка и опорно-двигательный аппарат",
        "prompt": """Ты — детский ортопед-травматолог.
Смотри на: осанку, плоскостопие, сколиоз, вальгус/варус, состояние суставов.
Учитывай возрастные нормы: лёгкое плоскостопие до 5-6 лет — вариант нормы.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с ортопедом»."""
    },
    {
        "id": "ophthalmologist",
        "name": "Офтальмолог",
        "focus": "Зрение",
        "prompt": """Ты — детский офтальмолог.
Смотри на: остроту зрения, косоглазие, миопию/гиперметропию, динамику ухудшения.
Учитывай: экранное время, освещение.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с офтальмологом»."""
    },
    {
        "id": "neurologist_child",
        "name": "Невролог (дет.)",
        "focus": "Нервная система и развитие",
        "prompt": """Ты — детский невролог.
Смотри на: психомоторное развитие по возрасту, сон, поведение, речь, ВЧД, судороги.
Используй нормы НПР (нервно-психического развития) по российским педиатрическим стандартам.
НИКОГДА не ставь диагнозы. Только «стоит обсудить с неврологом»."""
    },
]


def calculate_age(birthdate: date) -> dict:
    today = date.today()
    years = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    months = (today.month - birthdate.month) % 12
    return {"years": years, "months": months, "total_months": years * 12 + months}


def get_specialist_list(is_child: bool) -> list:
    return CHILD_SPECIALISTS if is_child else ADULT_SPECIALISTS


def run_single_agent(agent: dict, profile_data: dict, context: str, question: str = "") -> dict:
    """Запускает одного специализированного агента и возвращает его анализ."""
    age_info = calculate_age(profile_data["birthdate"])
    age_str = f"{age_info['years']} лет {age_info['months']} мес." if profile_data.get("is_child") else f"{age_info['years']} лет"

    system_prompt = f"""{agent['prompt']}

ПРОФИЛЬ ПАЦИЕНТА:
- Имя: {profile_data['name']}
- Возраст: {age_str}
- Группа крови: {profile_data.get('blood_type', 'не указана')}
- Аллергии: {', '.join(profile_data.get('allergies', [])) or 'нет данных'}
- Хронические состояния: {', '.join(profile_data.get('chronic_conditions', [])) or 'нет данных'}
- Семейный анамнез: {profile_data.get('family_history', {}) or 'нет данных'}

Отвечай ТОЛЬКО на русском языке.
Формат ответа строго JSON:
{{
  "severity": "low|medium|high",
  "findings": "краткое описание находок",
  "flags": ["список тревожных сигналов"],
  "gaps": ["какие данные отсутствуют"],
  "recommendations": ["что обсудить с врачом"],
  "summary": "1-2 предложения для итогового отчёта"
}}"""

    user_message = f"""ДАННЫЕ ПАЦИЕНТА:
{context}

{"ВОПРОС: " + question if question else "Проведи полный анализ в рамках своей специализации."}"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )

    import json
    try:
        text = response.content[0].text
        # Извлекаем JSON из ответа
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != 0:
            return {"agent": agent["name"], "data": json.loads(text[start:end])}
    except Exception:
        pass

    return {"agent": agent["name"], "data": {"severity": "low", "findings": response.content[0].text, "flags": [], "gaps": [], "recommendations": [], "summary": response.content[0].text[:200]}}


def run_consilium(profile_data: dict, context: str, problem: str) -> str:
    """Мультиагентный консилиум — запускает всех специалистов параллельно."""
    import concurrent.futures
    import json

    specialists = get_specialist_list(profile_data.get("is_child", True))
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(run_single_agent, agent, profile_data, context, problem): agent
            for agent in specialists
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                agent = futures[future]
                results.append({"agent": agent["name"], "data": {"severity": "low", "findings": f"Ошибка: {e}", "flags": [], "gaps": [], "recommendations": [], "summary": ""}})

    # Синтезирующий агент
    age_info = calculate_age(profile_data["birthdate"])
    synthesis_prompt = f"""Ты — главный врач-координатор. Обобщи заключения специалистов в единый план.

ПАЦИЕНТ: {profile_data['name']}, {age_info['years']} лет
ПРОБЛЕМА: {problem}

ЗАКЛЮЧЕНИЯ СПЕЦИАЛИСТОВ:
{json.dumps(results, ensure_ascii=False, indent=2)}

Составь итоговый отчёт на русском языке:
1. **Ключевые находки** (bullet-points, только важное)
2. **Приоритет действий** (срочно / в ближайшее время / наблюдение)
3. **Анализы для сдачи** (если нужны)
4. **К каким специалистам** (если нужно)
5. **Можно подождать** (что не требует срочного внимания)

Тон: профессиональный, понятный, без паники. Рекомендации — только для обсуждения с врачом."""

    synthesis = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": synthesis_prompt}]
    )

    return synthesis.content[0].text
