"""
Умный анализ трендов с автоматическим обнаружением аномалий.
Claude смотрит на динамику и сам говорит что важно.
"""
import os
import anthropic
from typing import List, Optional

client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))


def analyze_trend(marker_name: str, trend_points: list, profile_name: str, is_child: bool) -> str:
    """
    Анализирует тренд показателя и находит аномалии.
    trend_points: [{date, value, unit, status, ref_min, ref_max}]
    """
    if len(trend_points) < 2:
        return None  # Нечего анализировать — одна точка

    # Строим текстовое описание тренда
    trend_text = f"Показатель: {marker_name}\nПациент: {profile_name}\n\nДинамика:\n"
    for p in trend_points:
        status_label = {
            "normal": "норма",
            "high": "ВЫШЕ нормы",
            "low": "НИЖЕ нормы",
            "critical_high": "КРИТИЧЕСКИ высокий",
            "critical_low": "КРИТИЧЕСКИ низкий"
        }.get(p.get("status", "normal"), "норма")

        ref = ""
        if p.get("ref_min") and p.get("ref_max"):
            ref = f" (норма {p['ref_min']}–{p['ref_max']} {p.get('unit','')})"

        trend_text += f"  {p['date']}: {p['value']} {p.get('unit','')} — {status_label}{ref}\n"

    prompt = f"""{trend_text}

Ты — опытный врач-аналитик. Проанализируй динамику этого показателя.

{'Пациент — ребёнок. Учитывай возрастные нормы.' if is_child else 'Пациент — взрослый.'}

Найди:
1. Тренд (растёт / падает / стабильно / скачет)
2. Есть ли повод для беспокойства
3. Есть ли улучшение или ухудшение

Ответь КОРОТКО — 2-3 предложения максимум. Тон спокойный, без паники.
Начни с иконки: ✅ если всё хорошо, ⚠️ если стоит обратить внимание, 🔴 если срочно к врачу.
НИКОГДА не ставь диагнозы."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def detect_anomalies_in_labs(markers: list, profile_name: str, is_child: bool) -> Optional[str]:
    """
    Находит аномалии в наборе маркеров одного анализа.
    Возвращает текст только если есть что-то важное.
    """
    abnormal = [m for m in markers if m.get("status") not in ("normal", None, "")]
    if not abnormal:
        return None

    markers_text = "\n".join(
        f"  {m['name']}: {m['value']} {m.get('unit','')} — "
        f"{'ВЫШЕ' if m.get('status') in ('high','critical_high') else 'НИЖЕ'} нормы"
        f"{' (критично!)' if 'critical' in str(m.get('status','')) else ''}"
        for m in abnormal
    )

    prompt = f"""Пациент: {profile_name} {'(ребёнок)' if is_child else '(взрослый)'}

Отклонения в анализе:
{markers_text}

Ты — семейный врач. Коротко (2-3 предложения) объясни:
- На что обратить внимание
- Нужно ли срочно к врачу или просто при следующем визите упомянуть

Начни с: ⚠️ или 🔴 (если срочно).
НЕ ставь диагнозы."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def format_trend_with_analysis(
    marker_name: str,
    trend_points: list,
    profile_name: str,
    is_child: bool
) -> str:
    """Полный отчёт по тренду с AI-анализом для Telegram."""
    if not trend_points:
        return f"По показателю «{marker_name}» для {profile_name} данных нет."

    # Таблица значений
    lines = [f"📈 *{marker_name} — {profile_name}*\n"]
    for p in trend_points[-8:]:
        icon = "✅"
        if p.get("status") in ("high", "low"):
            icon = "🟡"
        elif p.get("status") in ("critical_high", "critical_low"):
            icon = "🔴"

        direction = ""
        if len(trend_points) > 1:
            idx = trend_points.index(p)
            if idx > 0:
                try:
                    prev = float(str(trend_points[idx-1]["value"]).replace(",", "."))
                    curr = float(str(p["value"]).replace(",", "."))
                    if curr > prev * 1.05:
                        direction = " ↑"
                    elif curr < prev * 0.95:
                        direction = " ↓"
                except (ValueError, TypeError):
                    pass

        ref = ""
        if p.get("ref_min") and p.get("ref_max"):
            ref = f" _(норма {p['ref_min']}–{p['ref_max']})_"

        lines.append(
            f"{icon} {p['date']}: *{p['value']}* {p.get('unit','')}{direction}{ref}"
        )

    # AI-анализ тренда (только если >= 2 точек)
    if len(trend_points) >= 2:
        analysis = analyze_trend(marker_name, trend_points, profile_name, is_child)
        if analysis:
            lines.append(f"\n{analysis}")

    return "\n".join(lines)
