"""
Единая точка входа для всех LLM-вызовов агентной системы.

Два режима:
- Mock (по умолчанию, если нет ключа): детерминированные ответы из mock_data.py,
  позволяет запускать демо и тесты без API
- Anthropic API: задайте ANTHROPIC_API_KEY (USE_MOCK=0/1 переключает принудительно)

Модель по умолчанию переопределяется переменной окружения CLAUDE_MODEL.
"""

import json
import os
import re
from pathlib import Path

from mock_data import (
    MOCK_KEY_POINTS,
    MOCK_INTERVIEWS,
    MOCK_ANALYSIS,
    MOCK_EDITED_TEXTS,
    MOCK_VALIDATION,
)


def _load_env():
    for p in [Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")

# На Opus 4.7+ параметры сэмплирования удалены из API — передача temperature вернёт 400
_NO_SAMPLING_MODELS = ("claude-opus-4-7", "claude-opus-4-8", "claude-fable")

_call_count = 0
_client = None

# Состояние мок-режима: номер итерации closed loop определяется по числу вызовов аналитика
_mock_state = {"analyst_calls": 0}


def get_call_count() -> int:
    return _call_count


def reset_call_count():
    global _call_count
    _call_count = 0
    _mock_state["analyst_calls"] = 0


def call_llm(model=DEFAULT_MODEL, messages=None, temperature=0.7, max_tokens=2048) -> str:
    """Вызов LLM: список messages (роли system/user/assistant) -> текст ответа."""
    global _call_count
    _call_count += 1
    messages = messages or []
    if _use_mock():
        return _mock_response(messages)
    return _api_call(model, messages, temperature, max_tokens)


def _use_mock() -> bool:
    flag = os.environ.get("USE_MOCK")
    if flag is not None:
        return flag.lower() not in ("0", "false", "")
    return not os.environ.get("ANTHROPIC_API_KEY")


# ─── Anthropic API ───

def _api_call(model: str, messages: list, temperature: float, max_tokens: int) -> str:
    import anthropic

    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=3)

    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    chat = [m for m in messages if m["role"] != "system"]

    kwargs = {"model": model, "max_tokens": max_tokens, "messages": chat}
    if system:
        kwargs["system"] = system
    if not model.startswith(_NO_SAMPLING_MODELS):
        kwargs["temperature"] = temperature

    response = _client.messages.create(**kwargs)
    return "".join(b.text for b in response.content if b.type == "text").strip()


# ─── Mock-режим ───

# Копия воронки из interview.SCRIPTED_QUESTIONS (прямой импорт невозможен: interview импортирует llm)
_MOCK_QUESTIONS = [
    "Прочитайте этот текст. Какое у вас первое впечатление? О чём этот текст?",
    "Что конкретно решил Центральный банк? Можете пересказать своими словами?",
    "Какие слова или фразы вам непонятны? Что бы вы хотели, чтобы объяснили проще?",
    "Этот текст вас тревожит, успокаивает или вам всё равно? Почему?",
    "После прочтения этого текста, вы что-то измените в своих финансовых делах? (вклады, кредиты, покупки)",
    "Вы доверяете тому, что написано? Почему да или нет?",
]

_MOCK_FALLBACK_PERSONA = "Ольга"


def _mock_response(messages: list) -> str:
    system = next((m["content"] for m in messages if m["role"] == "system"), "")

    if "извлечении ключевых смысловых точек" in system:
        return json.dumps(MOCK_KEY_POINTS, ensure_ascii=False)

    if "аналитик фокус-групп" in system:
        _mock_state["analyst_calls"] += 1
        iteration = min(_mock_state["analyst_calls"], len(MOCK_ANALYSIS))
        return json.dumps(MOCK_ANALYSIS[f"iteration_{iteration}"], ensure_ascii=False)

    if "редактор пресс-службы" in system:
        iteration = min(max(_mock_state["analyst_calls"], 1), len(MOCK_EDITED_TEXTS))
        return MOCK_EDITED_TEXTS[f"iteration_{iteration}"]

    if "валидатор качества" in system:
        return json.dumps(MOCK_VALIDATION, ensure_ascii=False)

    if "модератор фокус-группы" in system:
        asked = sum(1 for m in messages if m["role"] == "assistant")
        return _MOCK_QUESTIONS[asked % len(_MOCK_QUESTIONS)]

    persona_match = re.match(r"Ты — ([^,]+),", system)
    if persona_match:
        return _mock_persona_answer(persona_match.group(1).strip(), messages)

    return "Хорошо, понял. Расскажите подробнее, что вас интересует?"


def _mock_persona_answer(name: str, messages: list) -> str:
    iteration = min(_mock_state["analyst_calls"] + 1, len(MOCK_INTERVIEWS))
    answers_by_persona = MOCK_INTERVIEWS[f"iteration_{iteration}"]
    answers = answers_by_persona.get(name) or answers_by_persona[_MOCK_FALLBACK_PERSONA]
    # В диалоге персоны первый assistant-ход — подтверждение прочтения текста,
    # поэтому номер текущего вопроса = число assistant-сообщений минус один
    turn = sum(1 for m in messages if m["role"] == "assistant") - 1
    return answers[max(0, min(turn, len(answers) - 1))]
