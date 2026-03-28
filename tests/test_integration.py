"""
Интеграционные тесты: полный closed loop через реальный LLM (Haiku via Eliza).
Запуск: cd closed_loop && python -m pytest tests/test_integration.py -v
"""
import os
import pytest
from engine import run_closed_loop, extract_key_points
from interview import conduct_interview
from personas import PERSONAS
from channels import CHANNELS
from sample_releases import SAMPLE_RELEASES, DEFAULT_RELEASE
from llm import reset_call_count, get_call_count


class TestExtractKeyPoints:
    def test_returns_list(self):
        points = extract_key_points(DEFAULT_RELEASE)
        assert isinstance(points, list)
        assert len(points) >= 3

    def test_points_mention_rate(self):
        points = extract_key_points(DEFAULT_RELEASE)
        all_text = " ".join(points)
        assert "21" in all_text, "Key points should mention the rate 21%"


class TestInterview:
    def test_valentina_in_character(self):
        """Валентина: простой язык, тревога, без экспертных терминов."""
        reset_call_count()
        result = conduct_interview(DEFAULT_RELEASE, PERSONAS["valentina"], "valentina")
        assert result.persona_name == "Валентина"
        assert len(result.turns) == 6

        all_answers = " ".join(t.answer for t in result.turns).lower()
        # Не должна использовать экспертные термины
        for term in ["forward guidance", "спреды", "дку"]:
            assert term not in all_answers, f"Пенсионерка не должна говорить '{term}'"

    def test_alexey_expert_language(self):
        """Алексей: экспертное понимание, упоминает ставку."""
        reset_call_count()
        result = conduct_interview(DEFAULT_RELEASE, PERSONAS["alexey"], "alexey")
        all_answers = " ".join(t.answer for t in result.turns).lower()
        assert "ставк" in all_answers or "21" in all_answers

    def test_sergey_disengaged(self):
        """Сергей: скепсис, непонимание, простая речь."""
        reset_call_count()
        result = conduct_interview(DEFAULT_RELEASE, PERSONAS["sergey"], "sergey")
        all_answers = " ".join(t.answer for t in result.turns).lower()
        markers = ["не понял", "не понимаю", "не доверяю", "ерунда", "всё равно",
                    "не верю", "разводят", "непонятно"]
        found = any(m in all_answers for m in markers)
        assert found, f"Сергей должен показывать скепсис. Ответы: {all_answers[:200]}"

    def test_interview_serializable(self):
        reset_call_count()
        result = conduct_interview(DEFAULT_RELEASE, PERSONAS["olga"], "olga")
        d = result.to_dict()
        assert d["persona_name"] == "Ольга"
        assert len(d["turns"]) == 6


class TestClosedLoop:
    def test_full_loop(self):
        """Полный цикл с 2 персонами, 2 итерации."""
        reset_call_count()
        personas = {k: PERSONAS[k] for k in ["valentina", "alexey"]}
        result = run_closed_loop(DEFAULT_RELEASE, personas, max_iterations=2)

        assert len(result.iterations) >= 1
        assert len(result.scores) >= 1
        assert result.final_text != ""
        assert result.final_text != result.original_text
        assert "21" in result.final_text, "Решение по ставке должно быть сохранено"

    def test_analysis_has_structured_fields(self):
        """Анализ должен содержать score и problems."""
        reset_call_count()
        personas = {k: PERSONAS[k] for k in ["valentina"]}
        result = run_closed_loop(DEFAULT_RELEASE, personas, max_iterations=1)
        analysis = result.iterations[0].analysis

        assert "communication_score" in analysis
        score = analysis["communication_score"]
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    def test_text_simplified(self):
        """Финальный текст должен быть проще оригинала."""
        reset_call_count()
        personas = {k: PERSONAS[k] for k in ["valentina", "sergey"]}
        result = run_closed_loop(DEFAULT_RELEASE, personas, max_iterations=2)
        # Проблемная фраза должна быть убрана или переписана
        assert "автономное от решений Банка России" not in result.final_text

    def test_serialization(self):
        reset_call_count()
        personas = {k: PERSONAS[k] for k in ["valentina"]}
        result = run_closed_loop(DEFAULT_RELEASE, personas, max_iterations=1)
        d = result.to_dict()
        assert "original_text" in d
        assert "iterations" in d
        assert "scores" in d
        assert "final_text" in d


class TestChannels:
    def test_channel_runs(self):
        """Хотя бы один канал должен успешно прогоняться."""
        ch = CHANNELS["popular_vk"]
        reset_call_count()
        personas = {k: PERSONAS[k] for k in ch["audience_persona_keys"]}
        result = run_closed_loop(
            DEFAULT_RELEASE, personas,
            max_iterations=1, style_guide=ch["style_guide"],
        )
        assert len(result.iterations) == 1
        assert result.final_text != ""
