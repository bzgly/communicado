"""
Single benchmark run. Usage:
  python run_one.py release <release_index> [max_iter]
  python run_one.py channel <channel_key> [max_iter]

Results written to results/<name>.json
"""

import json
import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from engine import run_closed_loop
from llm import get_call_count, reset_call_count
from personas import PERSONAS
from channels import CHANNELS
from sample_releases import SAMPLE_RELEASES

os.makedirs("results", exist_ok=True)

releases = list(SAMPLE_RELEASES.items())


def save(name, result, persona_keys, elapsed):
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
        "final_text": result.final_text,
        "iterations": [
            {
                "iteration": it.iteration,
                "score": it.analysis.get("communication_score", 0),
                "problems": it.analysis.get("problems", []),
                "strengths": it.analysis.get("strengths", []),
                "readability": it.readability,
                "text": it.text,
            }
            for it in result.iterations
        ],
    }

    safe_name = name.replace(" ", "_").replace("/", "_").replace("·", "-")
    path = f"results/{safe_name}.json"
    with open(path, "w") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {path}")
    print(f"  Scores: {result.scores}")
    print(f"  Flesch: {orig_r.get('flesch_ru',0):.0f} -> {final_r.get('flesch_ru',0):.0f}")
    print(f"  Calls: {calls}, Time: {elapsed:.0f}s")


def run_release(idx, max_iter=3):
    key, text = releases[idx]
    name = f"6перс {key}"
    persona_keys = list(PERSONAS.keys())
    reset_call_count()
    t0 = time.time()
    result = run_closed_loop(text, {k: PERSONAS[k] for k in persona_keys}, max_iterations=max_iter, adaptive_interview=True)
    save(name, result, persona_keys, time.time() - t0)


def run_channel(ch_key, max_iter=3):
    ch = CHANNELS[ch_key]
    key, text = releases[-1]  # last release
    name = f"{ch['name']} {key}"
    persona_keys = ch["audience_persona_keys"]
    reset_call_count()
    t0 = time.time()
    result = run_closed_loop(
        text, {k: PERSONAS[k] for k in persona_keys},
        max_iterations=max_iter, style_guide=ch["style_guide"],
        adaptive_interview=True,
    )
    save(name, result, persona_keys, time.time() - t0)


if __name__ == "__main__":
    mode = sys.argv[1]
    arg = sys.argv[2]
    max_iter = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    if mode == "release":
        run_release(int(arg), max_iter)
    elif mode == "channel":
        run_channel(arg, max_iter)
