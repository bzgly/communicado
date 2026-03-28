"""
Объективные метрики читаемости текста (не LLM-based).
Закрывает пробел по Лекции 2: количественный текстовый анализ.

Метрики:
- Средняя длина предложения (слов)
- Средняя длина слова (символов)
- Доля сложных слов (>4 слогов)
- Flesch Reading Ease (адаптация для русского)
- Количество терминов из стоп-листа ЦБ

Литература:
- Bholat et al. (2019, BoE): упрощение языка повышает понятность на ~40%
- Оборнева И.В. (2006): адаптация формулы Flesch для русского языка
"""

import re

# Термины ЦБ, непонятные широкой аудитории (из реальных интервью)
CB_JARGON = [
    "ключевая ставка", "инфляционное давление", "инфляционные ожидания",
    "денежно-кредитные условия", "денежно-кредитная политика",
    "автономное ужесточение", "устойчивое инфляционное",
    "дефицит трудовых ресурсов", "целесообразность повышения",
    "разовые факторы", "на стороне предложения", "на стороне спроса",
    "базовый сценарий", "проинфляционные риски", "дезинфляционные",
    "трансмиссионный механизм", "таргетирование инфляции",
    "процентный канал", "кредитный канал",
]


def count_syllables_ru(word: str) -> int:
    """Подсчёт слогов в русском слове (по гласным)."""
    return len(re.findall(r'[аеёиоуыэюяАЕЁИОУЫЭЮЯ]', word))


def compute_readability(text: str) -> dict:
    """Вычисляет метрики читаемости текста."""
    # Разбиваем на предложения
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Разбиваем на слова
    words = re.findall(r'[а-яёА-ЯЁa-zA-Z]+', text)

    if not words or not sentences:
        return {
            "avg_sentence_length": 0,
            "avg_word_length": 0,
            "complex_word_ratio": 0,
            "flesch_ru": 0,
            "jargon_count": 0,
            "jargon_terms": [],
            "total_words": 0,
            "total_sentences": 0,
        }

    # Средняя длина предложения (в словах)
    words_per_sentence = [
        len(re.findall(r'[а-яёА-ЯЁa-zA-Z]+', s)) for s in sentences
    ]
    avg_sentence_length = sum(words_per_sentence) / len(words_per_sentence)

    # Средняя длина слова (в символах)
    avg_word_length = sum(len(w) for w in words) / len(words)

    # Доля сложных слов (>4 слогов)
    complex_words = [w for w in words if count_syllables_ru(w) > 4]
    complex_word_ratio = len(complex_words) / len(words)

    # Среднее число слогов на слово
    total_syllables = sum(count_syllables_ru(w) for w in words)
    avg_syllables = total_syllables / len(words)

    # Flesch Reading Ease (адаптация для русского)
    # Оборнева (2006): FRE_ru = 206.835 - 1.3 * ASL - 60.1 * ASW
    # ASL = avg sentence length, ASW = avg syllables per word
    flesch_ru = 206.835 - 1.3 * avg_sentence_length - 60.1 * avg_syllables
    flesch_ru = max(0, min(100, flesch_ru))

    # Термины из стоп-листа
    text_lower = text.lower()
    found_jargon = [term for term in CB_JARGON if term in text_lower]

    sentiment = compute_sentiment(text)

    return {
        "avg_sentence_length": round(avg_sentence_length, 1),
        "avg_word_length": round(avg_word_length, 1),
        "complex_word_ratio": round(complex_word_ratio, 3),
        "flesch_ru": round(flesch_ru, 1),
        "jargon_count": len(found_jargon),
        "jargon_terms": found_jargon,
        "total_words": len(words),
        "total_sentences": len(sentences),
        "sentiment_balance": sentiment["sentiment_balance"],
        "anxiety_words": sentiment["anxiety_words"],
        "reassurance_words": sentiment["reassurance_words"],
    }


# ─── Словарный сентимент-анализ (Лекция 2: количественный текстовый анализ) ───
# Минимальный словарь тревожных/успокаивающих слов в контексте ДКП.
# Подход из Лекции 2: dictionary-based sentiment, не требует обучения модели.

ANXIETY_WORDS = [
    "рост цен", "инфляция", "давление", "ужесточение", "замедление",
    "дефицит", "риски", "повышение", "ограничения", "высоким",
    "растут", "дорожает", "дорожать", "падение", "кризис",
    "проблема", "тревога", "беспокоит", "опасения",
]

REASSURANCE_WORDS = [
    "снижение", "стабилизация", "восстановление", "рост экономики",
    "вернётся к цели", "замедление инфляции", "снизится",
    "улучшение", "уверенность", "контроль", "поддержка",
    "выгодно", "доступно", "защита", "гарантия",
]


def compute_sentiment(text: str) -> dict:
    """Словарный сентимент: баланс тревожных vs успокаивающих слов."""
    text_lower = text.lower()
    anxiety_found = [w for w in ANXIETY_WORDS if w in text_lower]
    reassurance_found = [w for w in REASSURANCE_WORDS if w in text_lower]

    total = len(anxiety_found) + len(reassurance_found)
    if total == 0:
        balance = 0.0
    else:
        balance = (len(reassurance_found) - len(anxiety_found)) / total

    return {
        "anxiety_words": len(anxiety_found),
        "reassurance_words": len(reassurance_found),
        "sentiment_balance": round(balance, 2),  # -1 = тревожный, +1 = успокаивающий
        "anxiety_terms": anxiety_found,
        "reassurance_terms": reassurance_found,
    }


def readability_delta(before: dict, after: dict) -> dict:
    """Вычисляет изменение метрик (after - before)."""
    return {
        "flesch_ru_delta": round(after["flesch_ru"] - before["flesch_ru"], 1),
        "avg_sentence_delta": round(after["avg_sentence_length"] - before["avg_sentence_length"], 1),
        "jargon_delta": after["jargon_count"] - before["jargon_count"],
        "complex_word_delta": round(after["complex_word_ratio"] - before["complex_word_ratio"], 3),
    }
