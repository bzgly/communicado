"""
Closed-loop engine: extract → interview → analyze → edit → validate → repeat.

Литературное обоснование:
- СФГ Банка России (Лекция 3): "эксперименты с ИИ-модератором очень перспективны"
- Argyle et al. (2023): LLM как silicon samples, ρ ≈ 0.85 с реальными данными
- Horton (2023): "Homo Silicus" — LLM воспроизводят поведенческие эксперименты
- Bholat et al. (2019, BoE): упрощение языка повышает понятность на ~40%
"""

import json
import logging
import re
from dataclasses import dataclass, field
from interview import conduct_interview, InterviewResult
from llm import call_llm, reset_call_count
from readability import compute_readability, readability_delta
from prompts import ANALYST_SYSTEM, EDITOR_SYSTEM, VALIDATOR_SYSTEM, EXTRACTOR_SYSTEM

logger = logging.getLogger("closed_loop.engine")

MAX_EDIT_RETRIES = 2  # сколько раз переписывать если валидатор отклонил


@dataclass
class IterationResult:
    iteration: int
    text: str
    interviews: list[InterviewResult]
    analysis: dict
    validation: dict
    readability: dict = field(default_factory=dict)


@dataclass
class LoopResult:
    original_text: str
    key_points: list[str]
    iterations: list[IterationResult] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    final_text: str = ""
    original_readability: dict = field(default_factory=dict)
    final_readability: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "original_text": self.original_text,
            "key_points": self.key_points,
            "iterations": [
                {
                    "iteration": it.iteration,
                    "text": it.text,
                    "interviews": [iv.to_dict() for iv in it.interviews],
                    "analysis": it.analysis,
                    "validation": it.validation,
                    "readability": it.readability,
                }
                for it in self.iterations
            ],
            "scores": self.scores,
            "final_text": self.final_text,
            "original_readability": self.original_readability,
            "final_readability": self.final_readability,
        }


def extract_key_points(text: str) -> list[str]:
    raw = call_llm(
        messages=[
            {"role": "system", "content": EXTRACTOR_SYSTEM},
            {"role": "user", "content": text},
        ],
        temperature=0.3,
    )
    try:
        data = json.loads(_strip_markdown(raw))
        return data.get("key_points", [raw])
    except (json.JSONDecodeError, AttributeError):
        return [text[:200]]


def analyze_interviews(
    interviews: list[InterviewResult],
    text: str,
    iteration: int = 1,
    prev_score: int | None = None,
    prev_problems: list | None = None,
) -> dict:
    transcripts = "\n\n---\n\n".join(iv.full_transcript() for iv in interviews)
    prompt = f"Текст пресс-релиза:\n{text}\n\nСтенограммы интервью:\n{transcripts}"

    if iteration > 1 and prev_score is not None:
        prompt += (
            f"\n\n--- КОНТЕКСТ ---\n"
            f"Это итерация #{iteration} closed loop. "
            f"Предыдущая версия текста получила communication_score={prev_score}. "
            f"Проблемы предыдущей версии: {json.dumps(prev_problems or [], ensure_ascii=False)[:500]}. "
            f"Текст был переработан для устранения этих проблем. "
            f"Оцени ТЕКУЩУЮ версию объективно — если проблемы устранены, score должен вырасти."
        )

    raw = call_llm(
        messages=[
            {"role": "system", "content": ANALYST_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=4096,
    )
    try:
        return json.loads(_strip_markdown(raw))
    except json.JSONDecodeError:
        try:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except (json.JSONDecodeError, AttributeError):
            pass
        logger.warning(f"Failed to parse analyst response: {raw[:200]}")
        return {"communication_score": 50, "problems": [], "summary": raw[:300]}


def edit_text(text: str, analysis: dict, key_points: list[str], style_guide: str = "") -> str:
    prompt = (
        f"Оригинальный текст:\n{text}\n\n"
        f"Ключевые тезисы (ОБЯЗАТЕЛЬНО сохранить):\n"
        + "\n".join(f"- {p}" for p in key_points)
        + f"\n\nОтчёт аналитика:\n{json.dumps(analysis, ensure_ascii=False, indent=2)}"
    )
    if style_guide:
        prompt += f"\n\nСтилистические требования канала:\n{style_guide}"

    return call_llm(
        messages=[
            {"role": "system", "content": EDITOR_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
    )


def validate_text(key_points: list[str], new_text: str) -> dict:
    prompt = (
        f"Ключевые тезисы оригинала:\n"
        + "\n".join(f"{i+1}. {p}" for i, p in enumerate(key_points))
        + f"\n\nПереписанный текст:\n{new_text}"
    )
    raw = call_llm(
        messages=[
            {"role": "system", "content": VALIDATOR_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    try:
        return json.loads(_strip_markdown(raw))
    except json.JSONDecodeError:
        return {"valid": False, "points_check": [], "_parse_error": True}


def run_closed_loop(
    release_text: str,
    personas: dict,
    max_iterations: int = 10,
    score_threshold: float = 2.0,
    style_guide: str = "",
    adaptive_interview: bool = False,
) -> LoopResult:
    """Run the full closed loop with validation retry and readability metrics."""
    reset_call_count()

    key_points = extract_key_points(release_text)
    original_readability = compute_readability(release_text)

    result = LoopResult(
        original_text=release_text,
        key_points=key_points,
        original_readability=original_readability,
    )
    current_text = release_text

    for i in range(max_iterations):
        logger.info(f"=== Iteration {i+1}/{max_iterations} ===")

        # Interview all personas
        interviews = []
        for pkey, persona in personas.items():
            iv = conduct_interview(
                current_text, persona,
                persona_key=pkey,
                adaptive=adaptive_interview,
            )
            interviews.append(iv)

        # Analyze (with context from previous iteration)
        prev_score = result.scores[-1] if result.scores else None
        prev_problems = result.iterations[-1].analysis.get("problems") if result.iterations else None
        analysis = analyze_interviews(
            interviews, current_text,
            iteration=i + 1,
            prev_score=prev_score,
            prev_problems=prev_problems,
        )
        score = analysis.get("communication_score", 50)

        # Edit with validation retry
        new_text = current_text
        validation = {"valid": False}
        for retry in range(MAX_EDIT_RETRIES + 1):
            new_text = edit_text(current_text, analysis, key_points, style_guide)
            validation = validate_text(key_points, new_text)

            if validation.get("valid", False):
                break
            elif retry < MAX_EDIT_RETRIES:
                logger.warning(
                    f"Validation failed (attempt {retry+1}), re-editing. "
                    f"Lost points: {[p for p in validation.get('points_check', []) if not p.get('preserved')]}"
                )
                # Add validation feedback to analysis for the editor
                analysis["_validation_feedback"] = (
                    "ПРЕДЫДУЩАЯ ВЕРСИЯ НЕ ПРОШЛА ВАЛИДАЦИЮ. "
                    "Потеряны тезисы: " +
                    str([p for p in validation.get("points_check", []) if not p.get("preserved")])
                )

        # Compute readability for the new text
        text_readability = compute_readability(new_text)

        iteration = IterationResult(
            iteration=i + 1,
            text=new_text,
            interviews=interviews,
            analysis=analysis,
            validation=validation,
            readability=text_readability,
        )
        result.iterations.append(iteration)
        result.scores.append(score)

        current_text = new_text

        # Check convergence
        if len(result.scores) >= 2:
            delta = abs(result.scores[-1] - result.scores[-2])
            if delta < score_threshold:
                logger.info(f"Converged at iteration {i+1} (delta={delta:.1f})")
                break

    result.final_text = result.iterations[-1].text if result.iterations else release_text
    result.final_readability = compute_readability(result.final_text)
    return result


def _strip_markdown(text: str) -> str:
    """Remove ```json ... ``` wrappers from LLM response."""
    text = text.strip()
    m = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
