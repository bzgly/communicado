"""
Multi-turn interview: LLM-interviewer agent <-> persona agent.

Два режима:
1. Scripted (по умолчанию): фиксированные 6 вопросов воронки
2. Adaptive: LLM-интервьюер генерирует follow-up на основе ответов

Scripted режим обеспечивает воспроизводимость и стабильность.
Adaptive режим ближе к реальной фокус-группе (СФГ, Лекция 3).
"""

from dataclasses import dataclass, field
from prompts import build_persona_prompt, INTERVIEWER_SYSTEM
from llm import call_llm


# Фиксированные вопросы (воронка из методологии фокус-групп)
SCRIPTED_QUESTIONS = [
    "Прочитайте этот текст. Какое у вас первое впечатление? О чём этот текст?",
    "Что конкретно решил Центральный банк? Можете пересказать своими словами?",
    "Какие слова или фразы вам непонятны? Что бы вы хотели, чтобы объяснили проще?",
    "Этот текст вас тревожит, успокаивает или вам всё равно? Почему?",
    "После прочтения этого текста, вы что-то измените в своих финансовых делах? (вклады, кредиты, покупки)",
    "Вы доверяете тому, что написано? Почему да или нет?",
]


@dataclass
class InterviewTurn:
    question: str
    answer: str


@dataclass
class InterviewResult:
    persona_name: str
    persona_key: str
    turns: list[InterviewTurn] = field(default_factory=list)
    summary: str = ""
    mode: str = "scripted"

    def to_dict(self) -> dict:
        return {
            "persona_name": self.persona_name,
            "persona_key": self.persona_key,
            "turns": [{"question": t.question, "answer": t.answer} for t in self.turns],
            "summary": self.summary,
            "mode": self.mode,
        }

    def full_transcript(self) -> str:
        lines = [f"Интервью с {self.persona_name} ({self.mode}):"]
        for t in self.turns:
            lines.append(f"В: {t.question}")
            lines.append(f"О: {t.answer}")
        return "\n".join(lines)


def conduct_interview(
    text: str,
    persona: dict,
    persona_key: str = "unknown",
    adaptive: bool = False,
    max_turns: int = 6,
) -> InterviewResult:
    """Run interview with one persona.

    adaptive=False: scripted questions (stable, reproducible)
    adaptive=True: LLM-interviewer generates questions (closer to real focus group)
    """
    if adaptive:
        return _adaptive_interview(text, persona, persona_key, max_turns)
    return _scripted_interview(text, persona, persona_key)


def _scripted_interview(text: str, persona: dict, persona_key: str) -> InterviewResult:
    """Scripted mode: fixed questions, stable and reproducible."""
    persona_prompt = build_persona_prompt(persona)
    result = InterviewResult(
        persona_name=persona["name"],
        persona_key=persona_key,
        mode="scripted",
    )

    conversation = [
        {"role": "user", "content": f"Прочитай этот текст пресс-релиза ЦБ:\n\n{text}"},
        {"role": "assistant", "content": "Хорошо, я прочитал(а) текст. Готов(а) ответить на вопросы."},
    ]

    for q in SCRIPTED_QUESTIONS:
        conversation.append({"role": "user", "content": q})
        answer = call_llm(
            messages=[{"role": "system", "content": persona_prompt}] + conversation,
            temperature=0.8,
        )
        conversation.append({"role": "assistant", "content": answer})
        result.turns.append(InterviewTurn(question=q, answer=answer))

    result.summary = f"Scripted интервью с {persona['name']}: {len(result.turns)} вопросов."
    return result


def _adaptive_interview(
    text: str, persona: dict, persona_key: str, max_turns: int
) -> InterviewResult:
    """Adaptive mode: LLM-interviewer generates questions based on answers."""
    persona_prompt = build_persona_prompt(persona)
    result = InterviewResult(
        persona_name=persona["name"],
        persona_key=persona_key,
        mode="adaptive",
    )

    # Интервьюер получает контекст + историю
    interviewer_context = (
        f"Ты проводишь интервью о следующем тексте пресс-релиза ЦБ:\n\n{text}\n\n"
        f"Участник: {persona['name']}, {persona['age']} лет, {persona['profession']}, "
        f"{persona['city']}. Финансовая грамотность: {persona['knowledge_level']}.\n\n"
        f"Задай первый вопрос."
    )

    interviewer_history = [
        {"role": "system", "content": INTERVIEWER_SYSTEM},
        {"role": "user", "content": interviewer_context},
    ]

    persona_conversation = [
        {"role": "user", "content": f"Прочитай этот текст пресс-релиза ЦБ:\n\n{text}"},
        {"role": "assistant", "content": "Хорошо, я прочитал(а) текст. Готов(а) ответить на вопросы."},
    ]

    for turn_num in range(max_turns):
        # Интервьюер генерирует вопрос
        question = call_llm(messages=interviewer_history, temperature=0.6)

        # Персона отвечает
        persona_conversation.append({"role": "user", "content": question})
        answer = call_llm(
            messages=[{"role": "system", "content": persona_prompt}] + persona_conversation,
            temperature=0.8,
        )
        persona_conversation.append({"role": "assistant", "content": answer})

        result.turns.append(InterviewTurn(question=question, answer=answer))

        # Обновляем историю интервьюера
        interviewer_history.append({"role": "assistant", "content": question})
        interviewer_history.append({
            "role": "user",
            "content": f"Участник ответил: \"{answer}\"\n\nЗадай следующий вопрос. "
                       f"(Вопрос {turn_num + 2} из {max_turns}. "
                       f"{'Последний вопрос — подведи итог.' if turn_num == max_turns - 2 else ''})"
        })

    result.summary = f"Adaptive интервью с {persona['name']}: {len(result.turns)} вопросов."
    return result
