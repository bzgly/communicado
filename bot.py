"""
Telegram-бот: персональная коммуникация ЦБ.

Пользователь рассказывает о себе → бот строит персону →
прогоняет пресс-релиз через closed loop с этой персоной →
отдаёт персонализированный текст + отвечает на вопросы.

Запуск: python bot.py
"""

import asyncio
import logging
import json
import re
import os
from pathlib import Path
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters,
)

from llm import call_llm
from prompts import build_persona_prompt, ANALYST_SYSTEM, EDITOR_SYSTEM
from interview import conduct_interview
from engine import (
    run_closed_loop, extract_key_points, analyze_interviews,
    edit_text, validate_text, _strip_markdown,
)
from readability import compute_readability
from sample_releases import DEFAULT_RELEASE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("bot")

ONBOARDING, CHAT = range(2)
MAX_ONBOARDING_TURNS = 12

# ─── Load .env ───
def _load_env():
    for p in [Path(__file__).parent.parent / ".env", Path(__file__).parent / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_load_env()
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ─── Prompts ───
ONBOARDING_SYSTEM = """Ты — дружелюбный бот Банка России. Узнай о человеке, чтобы составить профиль.

Задай вопросы (по одному!) о:
1. Возраст и город
2. Профессия / чем занимается
3. Есть ли ипотека, кредиты
4. Есть ли сбережения, вклады
5. Откуда узнаёт экономические новости
6. Что беспокоит в экономике
7. Как относится к Центральному банку (доверяет/нет)

Когда узнаешь достаточно (минимум 5 пунктов), ответь РОВНО:
```json
{"ready": true, "profile": {"name": "...", "age": ..., "profession": "...", "city": "...", "concerns": "...", "financial_behavior": "...", "information_sources": "...", "knowledge_level": "...", "trust_level": "высокое/среднее/низкое", "emotional_tone": "...", "key_concerns": "..."}}
```

Говори коротко, тепло, на простом русском. НЕ упоминай что составляешь профиль."""


PERSONALIZE_SYSTEM = """Ты — персональный консультант Банка России. Перепиши пресс-релиз ЛИЧНО для этого человека:

- Учитывай его ситуацию (ипотека, вклады, бизнес, пенсия)
- Если ипотека — расскажи что будет со ставкой и платежами
- Если вклады — расскажи что с процентами, выгодно ли сейчас
- Если бизнес — расскажи что с кредитами для бизнеса
- Если пенсионер — успокой и объясни простым языком
- Если молодой и не разбирается — объясни базово, без терминов
- Соблюдай задачи коммуникационной политики ЦБ:
  * Якорение инфляционных ожиданий к цели 4%
  * Повышение доверия к ЦБ
  * Понятность для конкретного человека
- НЕ давай инвестиционных рекомендаций
- Пиши кратко (до 1500 символов), структурированно
- Заканчивай: "Есть вопросы? Спрашивайте!"
"""

QA_SYSTEM = """Ты — консультант Банка России. Отвечаешь на вопросы о решении по ставке.

Профиль пользователя:
{profile}

Пресс-релиз ЦБ:
{release}

Персонализированная версия (которую пользователь уже прочитал):
{personal}

Правила:
- Отвечай в контексте решения ЦБ И личной ситуации пользователя
- НЕ давай инвестрекомендаций ("купите", "продайте")
- Можешь объяснять механизмы ("при высокой ставке вклады выгоднее")
- Якорение ИО к цели 4% в 2026 году
- Пиши просто и коротко (до 800 символов)
"""


def _build_full_persona(raw: dict) -> dict:
    """Строим полную персону из ответов пользователя."""
    trust_map = {"высокое": 0.75, "среднее": 0.5, "низкое": 0.2}
    trust_str = raw.get("trust_level", "среднее")
    trust_val = trust_map.get(trust_str, 0.5)

    return {
        "name": raw.get("name", "Пользователь"),
        "age": raw.get("age", 35),
        "profession": raw.get("profession", "не указано"),
        "city": raw.get("city", "Россия"),
        "sentiment": min(1.0, max(0.0, trust_val)),
        "traits": raw.get("emotional_tone", "Обычный пользователь"),
        "concerns": raw.get("concerns", raw.get("key_concerns", "экономическая ситуация")),
        "key_phrases": "",
        "communication_style": "Обычная разговорная речь",
        "economic_view": raw.get("knowledge_level", "базовый"),
        "trust_in_institutions": trust_val,
        "knowledge_level": raw.get("knowledge_level", "базовый"),
        "financial_behavior": raw.get("financial_behavior", "не указано"),
        "policy_priority": "Стабильные цены, понятная политика ЦБ",
        "cb_functions_understanding": "Знает что ЦБ устанавливает ставку",
        "cb_perception": f"Доверие: {trust_str}",
        "cb_trust_factors": "Понятный язык, конкретные обещания",
        "information_sources": raw.get("information_sources", "интернет"),
        "emotional_tone": raw.get("emotional_tone", "Заинтересованный"),
    }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["onboarding_history"] = []
    context.user_data["onboarding_turns"] = 0
    await update.message.reply_text(
        "Привет! 👋 Я помогу разобраться в решениях Банка России.\n\n"
        "Расскажите немного о себе — так я смогу объяснить "
        "новости понятным именно вам языком.\n\n"
        "Сколько вам лет и из какого вы города?"
    )
    return ONBOARDING


async def onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    history = context.user_data.get("onboarding_history", [])
    turns = context.user_data.get("onboarding_turns", 0) + 1
    context.user_data["onboarding_turns"] = turns
    history.append({"role": "user", "content": user_text})

    try:
        response = await asyncio.to_thread(
            call_llm,
            messages=[{"role": "system", "content": ONBOARDING_SYSTEM}] + history,
            temperature=0.7,
            max_tokens=600,
        )
    except Exception as e:
        logger.error(f"LLM error in onboarding: {e}")
        await update.message.reply_text("Извините, произошла ошибка. Попробуйте ещё раз.")
        return ONBOARDING

    # Проверяем готовность
    if '"ready": true' in response or '"ready":true' in response:
        try:
            m = re.search(r'\{[^{}]*"ready"\s*:\s*true[^{}]*"profile"\s*:\s*\{[^}]+\}[^}]*\}', response, re.DOTALL)
            if not m:
                m = re.search(r'\{.*"ready".*true.*\}', response, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                if data.get("ready"):
                    return await _finish_onboarding(update, context, data.get("profile", {}))
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"JSON parse failed: {e}")

    # Fallback после MAX_ONBOARDING_TURNS
    if turns >= MAX_ONBOARDING_TURNS:
        # Собираем что есть из истории
        await update.message.reply_text("Спасибо! У меня достаточно информации. Подготовлю для вас объяснение...")
        return await _finish_onboarding(update, context, {"name": "Пользователь", "age": 35})

    # Продолжаем расспрос
    clean = response.split('```')[0].strip() if '```' in response else response
    history.append({"role": "assistant", "content": clean})
    context.user_data["onboarding_history"] = history
    await update.message.reply_text(clean)
    return ONBOARDING


async def _finish_onboarding(update, context, raw_profile):
    """Построить персону, прогнать closed loop, отправить результат."""
    persona = _build_full_persona(raw_profile)
    context.user_data["persona"] = persona
    context.user_data["profile_raw"] = raw_profile

    await update.message.reply_text(
        "Отлично! 🤝 Подготовлю персональное объяснение "
        "последнего решения Банка России...\n\n"
        "⏳ Это займёт 30-60 секунд."
    )

    try:
        personal_text = await asyncio.to_thread(_generate_personal_release, persona)
        context.user_data["personal_release"] = personal_text
        context.user_data["original_release"] = DEFAULT_RELEASE
        await update.message.reply_text(personal_text)
    except Exception as e:
        logger.error(f"LLM error generating release: {e}")
        await update.message.reply_text(
            "Извините, не удалось подготовить текст. Попробуйте /start заново."
        )
        return ConversationHandler.END

    context.user_data["chat_history"] = []
    return CHAT


BOT_MODEL = "claude-haiku-4-5-20251001"  # Haiku для скорости в боте


def _generate_personal_release(persona: dict) -> str:
    """Прогоняет closed loop с персоной пользователя (синхронно, в thread)."""
    import llm as llm_module
    original_model = llm_module.call_llm.__defaults__[0]
    # Временно переключаем на Haiku для скорости
    llm_module.call_llm.__defaults__ = (BOT_MODEL,) + llm_module.call_llm.__defaults__[1:]

    release = DEFAULT_RELEASE

    try:
        result = run_closed_loop(
            release,
            {"user": persona},
            max_iterations=2,
        )

        profile_summary = (
            f"{persona['name']}, {persona['age']} лет, {persona['profession']}, {persona['city']}. "
            f"Финансы: {persona['financial_behavior']}. "
            f"Беспокоит: {persona['concerns']}. "
            f"Новости: {persona['information_sources']}. "
            f"Доверие к ЦБ: {persona['cb_perception']}."
        )

        analysis = result.iterations[-1].analysis if result.iterations else {}

        personal = call_llm(
            messages=[
                {"role": "system", "content": PERSONALIZE_SYSTEM},
                {"role": "user", "content": (
                    f"Оригинальный пресс-релиз ЦБ:\n{release}\n\n"
                    f"Оптимизированная версия (после closed loop, Flesch {result.final_readability.get('flesch_ru', '?')}):\n"
                    f"{result.final_text}\n\n"
                    f"Профиль пользователя:\n{profile_summary}\n\n"
                    f"Обратная связь от интервью:\n{json.dumps(analysis, ensure_ascii=False)[:1500]}"
                )},
            ],
            temperature=0.7,
            max_tokens=1500,
        )
        return personal
    finally:
        llm_module.call_llm.__defaults__ = (original_model,) + llm_module.call_llm.__defaults__[1:]


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    persona = context.user_data.get("persona", {})
    release = context.user_data.get("original_release", DEFAULT_RELEASE)
    personal = context.user_data.get("personal_release", "")

    profile_str = json.dumps(persona, ensure_ascii=False, indent=2)[:800]

    history = context.user_data.get("chat_history", [])
    history.append({"role": "user", "content": user_text})

    try:
        response = await asyncio.to_thread(
            call_llm,
            messages=[
                {"role": "system", "content": QA_SYSTEM.format(
                    profile=profile_str,
                    release=release,
                    personal=personal[:1000],
                )},
            ] + history[-10:],
            temperature=0.7,
            max_tokens=800,
        )
    except Exception as e:
        logger.error(f"LLM error in chat: {e}")
        await update.message.reply_text("Извините, ошибка. Попробуйте переформулировать вопрос.")
        return CHAT

    history.append({"role": "assistant", "content": response})
    context.user_data["chat_history"] = history

    await update.message.reply_text(response)
    return CHAT


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Данные сброшены. /start — начать заново.")
    return ConversationHandler.END


def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not found in .env")
        return

    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    from telegram.request import HTTPXRequest
    kw = {"verify": ssl_context}
    request = HTTPXRequest(http_version="1.1", httpx_kwargs=kw)
    get_request = HTTPXRequest(http_version="1.1", httpx_kwargs=kw)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(get_request)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ONBOARDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding)],
            CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, chat)],
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("reset", reset)],
    )

    app.add_handler(conv)
    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
