"""
Прогоны closed loop по всем 4 пресс-релизам для презентации.

Конфигурации:
1. Каждый релиз × 3 персоны (Валентина, Сергей, Алексей) × 3 итерации
2. Последний релиз × 6 персон × 3 итерации
3. Последний релиз × канал "Народный ВК" × 3 итерации
4. Последний релиз × канал "Деловые СМИ" × 3 итерации
5. Последний релиз × канал "VK Клипы" × 3 итерации

Результаты пишутся в run_results_new.json
"""

import json
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from engine import run_closed_loop
from llm import get_call_count, reset_call_count
from personas import PERSONAS
from channels import CHANNELS
from sample_releases import SAMPLE_RELEASES

RESULTS = []
THREE_PERSONAS = ["valentina", "sergey", "alexey"]


def run_and_record(name, release_text, persona_keys, max_iter=3, style_guide=""):
    reset_call_count()
    personas = {k: PERSONAS[k] for k in persona_keys}
    t0 = time.time()
    result = run_closed_loop(
        release_text, personas,
        max_iterations=max_iter,
        style_guide=style_guide,
    )
    elapsed = time.time() - t0
    calls = get_call_count()

    orig_r = result.original_readability
    final_r = result.final_readability

    entry = {
        "name": name,
        "scores": result.scores,
        "flesch_before": orig_r.get("flesch_ru", 0),
        "flesch_after": final_r.get("flesch_ru", 0),
        "jargon_before": orig_r.get("jargon_count", 0),
        "jargon_after": final_r.get("jargon_count", 0),
        "sentiment_before": orig_r.get("sentiment_balance", 0),
        "sentiment_after": final_r.get("sentiment_balance", 0),
        "calls": calls,
        "elapsed_sec": round(elapsed, 1),
        "personas": persona_keys,
        "original_text": result.original_text[:200],
        "final_text": result.final_text,
    }
    RESULTS.append(entry)

    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  Scores: {result.scores}")
    print(f"  Flesch: {orig_r.get('flesch_ru',0):.0f} -> {final_r.get('flesch_ru',0):.0f}")
    print(f"  Jargon: {orig_r.get('jargon_count',0)} -> {final_r.get('jargon_count',0)}")
    print(f"  Calls: {calls}, Time: {elapsed:.0f}s")
    print(f"{'='*60}\n")

    # Сохраняем промежуточно
    with open("run_results_new.json", "w") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)

    return result


if __name__ == "__main__":
    releases = list(SAMPLE_RELEASES.items())

    # 1. Каждый релиз × 3 персоны
    for key, text in releases:
        run_and_record(
            f"3 перс · {key}",
            text, THREE_PERSONAS, max_iter=3,
        )

    # 2. Последний релиз × 6 персон
    last_key, last_text = releases[-1]
    run_and_record(
        f"6 перс · {last_key}",
        last_text, list(PERSONAS.keys()), max_iter=3,
    )

    # 3-5. Каналы на последнем релизе
    for ch_key in ["popular_vk", "business_media", "vk_clips"]:
        ch = CHANNELS[ch_key]
        run_and_record(
            f"{ch['name']} · {last_key}",
            last_text,
            ch["audience_persona_keys"],
            max_iter=3,
            style_guide=ch["style_guide"],
        )

    print(f"\nВсего прогонов: {len(RESULTS)}")
    print(f"Результаты в run_results_new.json")
