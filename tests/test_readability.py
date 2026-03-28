"""Unit-тесты для детерминированных метрик читаемости."""
from readability import compute_readability, compute_sentiment, readability_delta, count_syllables_ru


class TestSyllables:
    def test_simple_words(self):
        assert count_syllables_ru("мама") == 2
        assert count_syllables_ru("ставка") == 2
        assert count_syllables_ru("инфляция") == 4

    def test_one_syllable(self):
        assert count_syllables_ru("рост") == 1
        assert count_syllables_ru("банк") == 1


class TestReadability:
    def test_simple_text(self):
        text = "Ставка 21%. Цены растут."
        r = compute_readability(text)
        assert r["total_sentences"] == 2
        assert r["total_words"] >= 3
        assert r["flesch_ru"] > 0

    def test_complex_text_lower_flesch(self):
        simple = "Ставка осталась. Цены растут. Вклады выгодные."
        complex_ = (
            "Устойчивое инфляционное давление в совокупности с автономным "
            "ужесточением денежно-кредитных условий свидетельствует о "
            "необходимости поддержания жёстких параметров."
        )
        r_simple = compute_readability(simple)
        r_complex = compute_readability(complex_)
        assert r_simple["flesch_ru"] > r_complex["flesch_ru"]

    def test_jargon_detection(self):
        text = "Устойчивое инфляционное давление и инфляционные ожидания растут."
        r = compute_readability(text)
        assert r["jargon_count"] >= 2
        assert "инфляционное давление" in r["jargon_terms"]
        assert "инфляционные ожидания" in r["jargon_terms"]

    def test_no_jargon_in_simple_text(self):
        text = "Цены растут. Кредиты дорогие. Вклады выгодные."
        r = compute_readability(text)
        assert r["jargon_count"] == 0

    def test_empty_text(self):
        r = compute_readability("")
        assert r["total_words"] == 0
        assert r["flesch_ru"] == 0


class TestSentiment:
    def test_anxiety_text(self):
        text = "Рост цен, инфляция, ужесточение условий, дефицит ресурсов."
        s = compute_sentiment(text)
        assert s["anxiety_words"] >= 3
        assert s["sentiment_balance"] < 0

    def test_reassuring_text(self):
        text = "Снижение инфляции, восстановление экономики, контроль ситуации."
        s = compute_sentiment(text)
        assert s["reassurance_words"] >= 2
        assert s["sentiment_balance"] > 0

    def test_neutral_text(self):
        text = "Совет директоров принял решение."
        s = compute_sentiment(text)
        assert s["anxiety_words"] == 0
        assert s["reassurance_words"] == 0
        assert s["sentiment_balance"] == 0.0


class TestDelta:
    def test_improvement(self):
        before = {"flesch_ru": 14.0, "avg_sentence_length": 20.0, "jargon_count": 6, "complex_word_ratio": 0.2}
        after = {"flesch_ru": 40.0, "avg_sentence_length": 12.0, "jargon_count": 2, "complex_word_ratio": 0.1}
        d = readability_delta(before, after)
        assert d["flesch_ru_delta"] > 0
        assert d["avg_sentence_delta"] < 0
        assert d["jargon_delta"] < 0
