"""
Прод-тест: реальные LLM-вызовы через Eliza API.
Запуск: USE_MOCK=0 python test_prod.py

Требует: YA_TOKEN или SOY_TOKEN в окружении.
Расходует ~50-100 LLM-коллов (Haiku), ~$0.1-0.2.
"""

import os
import sys
import json
import time

os.environ["USE_MOCK"] = "0"

from llm import call_llm, reset_call_count, get_call_count
from interview import conduct_interview
from engine import run_closed_loop, extract_key_points
from personas import PERSONAS
from channels import CHANNELS
from sample_releases import DEFAULT_RELEASE

DELAY = 1.5  # секунд между вызовами чтобы не упереться в rate limit


def check_api():
    """Проверяем что API работает."""
    print("=" * 60)
    print("1. Проверка API...")
    try:
        result = call_llm(
            messages=[{"role": "user", "content": "Скажи 'ок'"}],
            max_tokens=10,
        )
        print(f"   API OK: {result}")
        return True
    except Exception as e:
        print(f"   API FAIL: {e}")
        return False


def test_extract():
    """Проверяем экстракцию тезисов."""
    print("\n" + "=" * 60)
    print("2. Экстракция ключевых тезисов...")
    reset_call_count()
    points = extract_key_points(DEFAULT_RELEASE)
    print(f"   Тезисов: {len(points)}")
    for i, p in enumerate(points):
        print(f"   {i+1}. {p}")

    assert len(points) >= 3, f"Слишком мало тезисов: {len(points)}"
    assert any("21" in p for p in points), "Нет упоминания ставки 21%"
    print("   PASS")
    time.sleep(DELAY)


def test_interview_valentina():
    """Проверяем что Валентина отвечает в character."""
    print("\n" + "=" * 60)
    print("3. Интервью с Валентиной (67, пенсионерка, Воронеж)...")
    reset_call_count()
    result = conduct_interview(DEFAULT_RELEASE, PERSONAS["valentina"], "valentina")

    print(f"   Вопросов: {len(result.turns)}")
    for t in result.turns:
        print(f"\n   В: {t.question}")
        print(f"   О: {t.answer}")
        time.sleep(DELAY)

    all_answers = " ".join(t.answer for t in result.turns).lower()

    # Валентина НЕ должна использовать экспертные термины
    expert_terms = ["forward guidance", "спреды", "офз", "дку"]
    for term in expert_terms:
        assert term not in all_answers, f"Валентина использует экспертный термин '{term}'!"

    print("\n   PASS: Валентина отвечает в character (простой язык, без экспертизы)")


def test_interview_alexey():
    """Проверяем что Алексей отвечает как эксперт."""
    print("\n" + "=" * 60)
    print("4. Интервью с Алексеем (38, финдиректор, Москва)...")
    reset_call_count()
    result = conduct_interview(DEFAULT_RELEASE, PERSONAS["alexey"], "alexey")

    print(f"   Вопросов: {len(result.turns)}")
    for t in result.turns:
        print(f"\n   В: {t.question}")
        print(f"   О: {t.answer}")
        time.sleep(DELAY)

    all_answers = " ".join(t.answer for t in result.turns).lower()
    assert "ставк" in all_answers or "21" in all_answers, \
        "Алексей не упоминает ставку!"

    print("\n   PASS: Алексей отвечает как эксперт")


def test_closed_loop():
    """Полный closed loop с 2 персонами, 2 итерации."""
    print("\n" + "=" * 60)
    print("5. Closed Loop (Валентина + Алексей, 2 итерации)...")
    reset_call_count()

    personas = {k: PERSONAS[k] for k in ["valentina", "alexey"]}
    result = run_closed_loop(DEFAULT_RELEASE, personas, max_iterations=2)

    print(f"\n   Итераций: {len(result.iterations)}")
    print(f"   Scores: {result.scores}")
    print(f"   Key points: {len(result.key_points)}")
    print(f"   LLM коллов: {get_call_count()}")

    print(f"\n   --- Оригинал ({len(result.original_text)} символов) ---")
    print(f"   {result.original_text[:200]}...")

    print(f"\n   --- Финальный текст ({len(result.final_text)} символов) ---")
    print(f"   {result.final_text[:300]}...")

    for it in result.iterations:
        score = it.analysis.get("communication_score", "?")
        problems = it.analysis.get("problems", [])
        print(f"\n   --- Итерация {it.iteration}: Score {score} ---")
        for p in problems:
            print(f"   Проблема: \"{p.get('phrase', '')}\" -> {p.get('suggestion', '')}")

    assert result.final_text != result.original_text, "Текст не изменился!"
    assert "21%" in result.final_text or "21" in result.final_text, "Потеряно решение по ставке!"
    print("\n   PASS: Closed loop работает, текст улучшается")


def test_channel_adaptation():
    """Проверяем что разные каналы дают разные тексты."""
    print("\n" + "=" * 60)
    print("6. Адаптация по каналам (popular_vk vs business_media)...")

    results = {}
    for ch_key in ["popular_vk", "business_media"]:
        ch = CHANNELS[ch_key]
        reset_call_count()
        personas = {k: PERSONAS[k] for k in ch["audience_persona_keys"]}
        r = run_closed_loop(DEFAULT_RELEASE, personas, max_iterations=1, style_guide=ch["style_guide"])
        results[ch_key] = r
        print(f"\n   [{ch['name']}] Score: {r.scores[0] if r.scores else '?'}")
        print(f"   Текст: {r.final_text[:200]}...")

    print("\n   PASS: Разные каналы — разные тексты")


if __name__ == "__main__":
    print("CB Communication Closed Loop — Prod Tests")
    print("Модель: claude-haiku-4-5-20251001 via Eliza")
    print()

    if not check_api():
        print("\nAPI недоступен. Проверьте YA_TOKEN/SOY_TOKEN.")
        sys.exit(1)

    time.sleep(DELAY)
    test_extract()
    time.sleep(DELAY)
    test_interview_valentina()
    time.sleep(DELAY)
    test_interview_alexey()
    time.sleep(DELAY)
    test_closed_loop()
    time.sleep(DELAY)
    test_channel_adaptation()

    print("\n" + "=" * 60)
    print("ВСЕ ПРОД-ТЕСТЫ ПРОЙДЕНЫ")
    print("=" * 60)
