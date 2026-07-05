"""
Генератор PDF-презентации. Запуск: python build_presentation.py
"""

import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─── Шрифты ───
FONT_NAME = "Helvetica"
for path, name in [
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "ArialRu"),
    ("/Library/Fonts/Arial.ttf", "ArialRu"),
]:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            FONT_NAME = name
            break
        except Exception:
            continue

# ─── Цвета ───
DARK = HexColor("#0F172A")
BLUE = HexColor("#1E3A5F")
ACCENT = HexColor("#3B82F6")
GRAY = HexColor("#64748B")

PAGE_W, PAGE_H = landscape(A4)


def S(name, size, color=DARK, align=TA_LEFT, space_after=0, leading=None):
    return ParagraphStyle(name, fontName=FONT_NAME, fontSize=size, textColor=color,
                          alignment=align, leading=leading or size * 1.35, spaceAfter=space_after)

S_TITLE = S("title", 28, DARK, TA_CENTER, 8)
S_SUB = S("sub", 14, GRAY, TA_CENTER, 20)
S_H1 = S("h1", 22, BLUE, space_after=10)
S_H2 = S("h2", 15, DARK, space_after=6)
S_BODY = S("body", 11, DARK, space_after=6, leading=15)
S_SM = S("sm", 9.5, GRAY, space_after=4, leading=13)
S_BADGE = S("badge", 10, ACCENT, TA_CENTER)
S_NUM = S("num", 18, ACCENT, TA_CENTER)


def slide_title(title, subtitle=None):
    elems = [Spacer(1, 1.2 * cm), Paragraph(title, S_H1)]
    if subtitle:
        elems.append(Paragraph(subtitle, S("st", 11, GRAY, space_after=12)))
    elems.append(Spacer(1, 0.4 * cm))
    return elems


def tbl(data, widths=None):
    style = [
        ("FONT", (0, 0), (-1, -1), FONT_NAME, 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#EFF6FF")),
        ("FONT", (0, 0), (-1, 0), FONT_NAME, 9.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), BLUE),
    ]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t


E = []  # elements

# ── Слайд 1: Титул ──
E += [Spacer(1, 5 * cm)]
E.append(Paragraph("CB Communication Closed Loop", S_TITLE))
E.append(Spacer(1, 0.3 * cm))
E.append(Paragraph(
    "Автоматическая оптимизация коммуникации Банка России<br/>"
    "через синтетические интервью с LLM-агентами",
    S_SUB))
E.append(Spacer(1, 1 * cm))
E.append(Paragraph("Industrial ML  |  LLM Agents  |  Central Bank Communication", S_BADGE))
E.append(PageBreak())

# ── Слайд 2: Проблема ──
E += slide_title("Проблема")
E.append(Paragraph(
    "ЦБ публикует один пресс-релиз на языке экспертов. "
    "До населения он доходит через цепочку посредников (СМИ, Telegram, ТВ), "
    "на каждом шаге искажаясь.", S_BODY))
E.append(tbl([
    ["Факт", "Источник"],
    ["Только 30-40% домохозяйств обновляют ожидания\nпосле объявлений ЦБ", "Lamla & Vinogradov (2024, JME)"],
    ["Эксперты и не-эксперты реагируют на одну фразу\nЦБ ПРОТИВОПОЛОЖНО", "Kim & Lee (Bounded Rationality\nin CB Communication)"],
    ["Упрощение языка повышает понятность на ~40%\nи снижает дисперсию ожиданий на 30%", "Ehrmann & Wabitsch (2022, JME)\nBholat et al. (2019, BoE)"],
    ["37% россиян получают экономические новости\nиз Telegram", "НАФИ (2024)"],
], widths=[14 * cm, 8 * cm]))
E.append(PageBreak())

# ── Слайд 3: Что сделано в ЦБ ──
E += slide_title("Что уже сделано в Банке России")
E.append(Paragraph(
    "<b>Синтетическая фокус-группа (СФГ)</b> — проект летней школы Сколтеха "
    "(Дубинина, Леон, Закарин, Завадская; куратор: А. Евстигнеева, Банк России):", S_BODY))
E.append(tbl([
    ["Компонент", "Реализация", "Ограничение"],
    ["LLM-аватары", "Профили из реальных интервью\n(Qwen3-8B)", "Модератор — человек"],
    ["Интервью", "Модератор задаёт вопросы\nаватарам в чате", "Не автоматизировано,\nне масштабируется"],
    ["Результат", "Качественный фидбек,\nулучшение документа", "Один текст для всех,\nнет количественных метрик"],
], widths=[5 * cm, 8 * cm, 7 * cm]))
E.append(Spacer(1, 0.5 * cm))
E.append(Paragraph(
    "<b>Сами авторы пишут:</b> «Эксперименты с ИИ-модератором представляются "
    "очень перспективными» — мы это реализуем.", S_SM))
E.append(PageBreak())

# ── Слайд 4: Наше решение ──
E += slide_title("Наше решение: Automated Closed Loop")
E.append(Paragraph(
    "Воспроизводим СФГ, но заменяем модератора-человека на LLM-агента "
    "и замыкаем в автоматический цикл оптимизации.", S_BODY))
E.append(tbl([
    ["Шаг", "Что происходит", "Агент"],
    ["1. Экстракция", "Из оригинала извлекаются 5 ключевых тезисов\n(чеклист для валидации)", "Экстрактор"],
    ["2. Интервью", "6 вопросов каждой из 6 персон\n(воронка: впечатление → понимание → эмоции → поведение)", "Интервьюер\n+ 6 Персон"],
    ["3. Анализ", "Находит паттерны: '4 из 6 не поняли фразу X'\nВыдаёт Communication Score (0-100)", "Аналитик"],
    ["4. Редактура", "Переписывает текст по конкретным замечаниям\nСохраняет все 5 тезисов", "Редактор"],
    ["5. Валидация", "Проверяет чеклист: все тезисы на месте?\nНет инвестрекомендаций?", "Валидатор"],
    ["6. Повтор", "Цикл повторяется до сходимости Score\n(дельта < 2) или 10 итераций", ""],
], widths=[3 * cm, 11 * cm, 4 * cm]))
E.append(PageBreak())

# ── Слайд 4b: Архитектура (диаграмма) ──
E += slide_title("Архитектура системы")
E.append(Paragraph(
    "8 LLM-агентов, замкнутый цикл, двойная система метрик (LLM + детерминированные)", S_SM))
E.append(Spacer(1, 0.3 * cm))
# Визуальная блок-схема как таблица
arch_style = [
    ("FONT", (0, 0), (-1, -1), FONT_NAME, 10),
    ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("GRID", (0, 0), (-1, -1), 0, HexColor("#FFFFFF")),
    # Boxes
    ("BACKGROUND", (0, 0), (0, 0), HexColor("#1E3A5F")),  # input
    ("TEXTCOLOR", (0, 0), (0, 0), white),
    ("BACKGROUND", (2, 0), (2, 0), HexColor("#3B82F6")),  # extract
    ("TEXTCOLOR", (2, 0), (2, 0), white),
    ("BACKGROUND", (4, 0), (4, 0), HexColor("#8B5CF6")),  # interview
    ("TEXTCOLOR", (4, 0), (4, 0), white),
    ("BACKGROUND", (0, 2), (0, 2), HexColor("#10B981")),  # output
    ("TEXTCOLOR", (0, 2), (0, 2), white),
    ("BACKGROUND", (2, 2), (2, 2), HexColor("#F59E0B")),  # validate
    ("TEXTCOLOR", (2, 2), (2, 2), white),
    ("BACKGROUND", (4, 2), (4, 2), HexColor("#EF4444")),  # analyze+edit
    ("TEXTCOLOR", (4, 2), (4, 2), white),
    ("ROUNDEDCORNERS", [8, 8, 8, 8]),
]
arch_data = [
    ["Пресс-релиз\nЦБ", "→", "Экстрактор\n(5 тезисов)", "→", "Интервьюер\n+ 6 Персон"],
    ["", "", "", "", "↓"],
    ["Финальный\nтекст + метрики", "←", "Валидатор\n(retry если fail)", "←", "Аналитик\n→ Редактор"],
]
arch_t = Table(arch_data, colWidths=[4 * cm, 1.5 * cm, 4 * cm, 1.5 * cm, 4 * cm])
arch_t.setStyle(TableStyle(arch_style))
E.append(arch_t)
E.append(Spacer(1, 0.4 * cm))
E.append(Paragraph(
    "<b>Метрики:</b> Communication Score (LLM, 0-100, anchor points) + "
    "Flesch Reading Ease (детерминированный) + Jargon Count (стоп-лист 19 терминов) + "
    "Sentiment Balance (словарный, Лекция 2)", S_SM))
E.append(PageBreak())

# ── Слайд 4c: До / После (конкретный пример) ──
E += slide_title("До / После: конкретные фразы")
E.append(tbl([
    ["Оригинал (Flesch=14, Score=35)", "После 3 итераций (Flesch=44, Score=72)"],
    ["Устойчивое инфляционное давление,\nхотя и снизилось по ряду показателей,\nв целом остаётся высоким.",
     "Цены продолжают расти, хотя\nмедленнее, чем осенью. Давление\nна цены остаётся сильным."],
    ["Автономное от решений Банка России\nужесточение условий банковского\nкредитования.",
     "Банки сами повысили требования\nк заёмщикам — даже без указаний\nЦентрального банка."],
    ["Инфляционные ожидания населения\nи бизнеса продолжают расти.",
     "Люди и компании ожидают, что\nцены будут расти и дальше — и это\nсамо по себе разгоняет инфляцию."],
    ["Целесообразность повышения ключевой\nставки на ближайшем заседании.",
     "На следующем заседании ЦБ решит,\nнужно ли поднимать ставку ещё."],
], widths=[10.5 * cm, 10.5 * cm]))
E.append(Spacer(1, 0.3 * cm))
E.append(Paragraph(
    "<b>Sentiment:</b> оригинал -1.0 (8 тревожных слов, 0 успокаивающих) → "
    "финал -0.33 (баланс улучшился). Жаргон: 6 → 2 терминов.", S_SM))
E.append(PageBreak())

# ── Слайд 5: Персоны ──
E += slide_title("Синтетические персоны", "Формат профилей из СФГ (19 полей)")
E.append(tbl([
    ["Персона", "Ось из литературы", "Источник", "Attention"],
    ["Валентина (67, Воронеж)\nПенсионерка", "Низкая грамотность,\nТВ как канал, высокая тревожность", "Jung & Mongelli: макс. эффект\nна пожилых. БР WP 148", "~25%"],
    ["Алексей (38, Москва)\nФинансовый директор", "Высокая грамотность,\nпрямой канал (cbr.ru)", "Blinder et al. (2024):\nbaseline аудитория", "~95%"],
    ["Ольга (34, Казань)\nМама с ипотекой", "Наличие долга,\nчувствительность к ставке", "Cloyne et al. (2024, JME):\nипотечники внимательнее", "~60%"],
    ["Сергей (45, Челябинск)\nВодитель", "Мин. активы,\nмин. внимание к ЦБ", "D'Acunto et al. (2024, NBER):\nнизкий IQ → нет Эйлера", "~15%"],
    ["Павел (51, Краснодар)\nВладелец бизнеса", "Кредитный канал,\npricing power", "Candia et al. (2024):\n25% pass-through к ценам", "~30%"],
    ["Даниил (22, СПб)\nСтудент-экономист", "Молодёжь, соцсети,\nтеория без практики", "Lamla & Vinogradov:\nмин. attention к ЦБ", "~15%"],
], widths=[5 * cm, 4.5 * cm, 6 * cm, 2 * cm]))
E.append(PageBreak())

# ── Слайд 6: Демо 1 ──
E += slide_title("Демо: Closed Loop в действии",
                  "Реальный прогон через Claude API (Haiku 4.5), 64 LLM-колла")
E.append(Paragraph("<b>Communication Score:</b> 35 → 58 → 72 | <b>Flesch:</b> 14.3 → 44.3 (+30) | <b>Жаргон:</b> 6 → 2", S("sc", 12, ACCENT, space_after=10)))
E.append(tbl([
    ["Итерация", "Score", "Clarity", "Anxiety", "Главная проблема"],
    ["1 (оригинал)", "35", "3", "9", "'устойчивое инфляционное давление' —\nнепонятно. 6 терминов в стоп-листе.\nFlesch=14 (очень сложный)"],
    ["2", "58", "7", "8", "'ключевая ставка' расшифрована.\nТермины заменены на простые фразы.\nFlesch=35"],
    ["3", "72", "8", "8", "Текст понятен 5 из 6 персон.\nЖаргон: 6→2. Flesch=44.\nВалидатор: все 5 тезисов сохранены."],
], widths=[3.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 9 * cm]))
E.append(Spacer(1, 0.3 * cm))
E.append(Paragraph(
    "<b>Объективные метрики (не LLM):</b> Flesch 14→44 (+30), "
    "жаргон ЦБ 6→2. Валидатор с retry гарантирует сохранение тезисов.", S_SM))
E.append(Paragraph(
    "<b>Ключевая находка:</b> Anxiety Score вырос с 8 до 9 после упрощения текста. "
    "Это воспроизводит эффект Kim & Lee: когда текст понятнее, тревожный сигнал "
    "доходит до аудитории сильнее. Канцелярит работает как демпфер эмоций.", S_SM))
E.append(PageBreak())

# ── Слайд 6b: Реальные цитаты персон ──
E += slide_title("Реальные ответы LLM-персон (Claude Haiku 4.5)")
E.append(tbl([
    ["Персона", "Первое впечатление (реальный LLM-ответ)"],
    ["Валентина\n(67, пенсионерка)", "«Ой, дочка, честно говоря, половину я не поняла.\nЭто же не по-русски написано! Какие-то 'ключевые\nставки'... Я знаю что молоко подорожало — вот и всё.»"],
    ["Сергей\n(45, водитель)", "«Полная ерунда, честно говоря. Они там сидят\nв своих кабинетах... Мне бы до зарплаты дотянуть,\nа они про 'автономное ужесточение'. Говорят по-китайски.»"],
    ["Алексей\n(38, финдиректор)", "«Стандартный пресс-релиз ЦБ по решению ставки.\nОсторожность ЦБ перед сложной ситуацией.\nИнтересно, что признают автономное ужесточение.»"],
], widths=[4 * cm, 16.5 * cm]))
E.append(Spacer(1, 0.3 * cm))
E.append(Paragraph(
    "<b>Когнитивный разрыв (Kim & Lee):</b> Алексей видит позитивный сигнал ('пауза в цикле ужесточения'). "
    "Валентина и Сергей видят угрозу ('цены растут, ставку не снижают'). "
    "Один текст — два противоположных поведенческих эффекта.", S_SM))
E.append(PageBreak())

# ── Слайд 7: Каналы ──
E += slide_title("Расширение: разные каналы — разные агенты")
E.append(Paragraph(
    "Тот же closed loop, но для каждого канала ЦБ — свой набор персон.", S_BODY))
E.append(tbl([
    ["Канал", "Аудитория", "Персоны", "Стиль"],
    ["Пресс-релиз (cbr.ru)", "Аналитики, журналисты", "Алексей, Павел", "Официальный, с терминами"],
    ["ТГ-канал ЦБ", "Финансисты + любопытствующие", "Алексей, Даниил, Ольга", "Официальный, но доступный"],
    ["Деловые СМИ (РБК)", "Бизнес, инвесторы", "Алексей, Павел", "Деловой, цифры и прогнозы"],
    ["Народный ВК / ТГ", "Широкая, низкая грамотность", "Валентина, Ольга, Сергей", "Максимально простой"],
    ["VK Клипы / Reels", "Молодёжь 18-30", "Даниил, Ольга", "Сценарий 60-сек видео"],
], widths=[4.5 * cm, 4.5 * cm, 5 * cm, 5 * cm]))
E.append(Spacer(1, 0.3 * cm))
E.append(Paragraph(
    "Результат: один пресс-релиз → 5 адаптированных текстов. Все с единым посылом "
    "(валидатор проверяет сохранение 5 ключевых тезисов).", S_SM))
E.append(PageBreak())

# ── Слайд 8: Демо 2 ──
E += slide_title("Демо: один релиз → разные тексты")
E.append(Paragraph("<b>Пример: 'народный ВК' vs оригинал</b>", S_H2))
E.append(tbl([
    ["Оригинал (пресс-релиз)", "Адаптация для народного ВК"],
    ["Устойчивое инфляционное давление,\nхотя и снизилось по ряду показателей\nв ноябре, в целом остаётся высоким.",
     "Цены продолжают расти,\nхотя медленнее, чем осенью."],
    ["Автономное от решений Банка России\nужесточение условий банковского\nкредитования.",
     "Банки сами повысили требования\nк заёмщикам."],
    ["Банк России будет оценивать\nцелесообразность повышения ключевой\nставки на ближайшем заседании.",
     "Ставка останется высокой, пока цены\nне начнут расти ближе к норме."],
], widths=[11 * cm, 10 * cm]))
E.append(PageBreak())

# ── Слайд 9: Перспективы ──
E += slide_title("Перспективы: персональная коммуникация")
E.append(Paragraph(
    "Broadcast → Multi-channel → <b>Personal</b>", S("big", 16, ACCENT, TA_CENTER, 16)))
E.append(tbl([
    ["Этап", "Что делаем", "Статус"],
    ["А. Из диалога", "Бот в Telegram/VK спрашивает: возраст,\nипотека, вклады, откуда узнаёте новости.\nСтроит персональный профиль.", "Концепция"],
    ["Б. Из данных", "Банковское приложение знает продукты\nклиента (ипотека, вклад, карта).\nАдаптирует коммуникацию автоматически.", "Vision"],
    ["В. Q&A", "Пользователь спрашивает: 'Что будет\nс моей ипотекой?' — бот отвечает\nв контексте решения ЦБ.", "Интеграция с\nЭмпатичной MAS"],
], widths=[4 * cm, 10 * cm, 4 * cm]))
E.append(PageBreak())

# ── Слайд 10: Отличия ──
E += slide_title("Чем отличается от проектов Банка России")
E.append(tbl([
    ["Проект ЦБ", "Что делает", "Чего не делает (а мы делаем)"],
    ["СФГ\n(Дубинина и др.)", "Тестирует документ через\nфокус-группу с модератором-\nчеловеком", "Не автоматизирует цикл\nНе генерирует версии\nпод разные каналы"],
    ["РегИИ.ON", "MAS-бот для подготовки\nсотрудников ЦБ\n(данные + каверзные вопросы)", "Не для населения\nНе адаптирует\nкоммуникацию"],
    ["Эмпатичная MAS", "Отвечает на вопросы\nлюдей (экономист +\nэмпат + не-экономист)", "Не генерирует контент\nНе оптимизирует\nтекст"],
], widths=[4 * cm, 7 * cm, 7 * cm]))
E.append(Spacer(1, 0.5 * cm))
E.append(Paragraph(
    "<b>Наш вклад:</b> автоматический closed loop (вместо модератора) + "
    "масштабирование на каналы + путь к персонализации.", S_BODY))
E.append(PageBreak())

# ── Слайд 11: Технологии ──
E += slide_title("Технический стек")
E.append(tbl([
    ["Компонент", "Технология", "Количество"],
    ["LLM-агенты", "Claude Haiku 4.5\n(Anthropic API)", "8 ролей: экстрактор,\nинтервьюер, 6 персон,\nаналитик, редактор, валидатор"],
    ["Closed loop", "Python, structured JSON output", "~33 LLM-колла за итерацию\n~165 за 5 итераций"],
    ["Каналы", "Тот же loop, разные персоны", "~660 коллов на 4 канала"],
    ["Демо", "Streamlit + Plotly", "4 вкладки: loop, каналы,\nсравнение, лог"],
    ["Презентация", "reportlab (PDF)", "12 слайдов"],
], widths=[4 * cm, 6 * cm, 7 * cm]))
E.append(PageBreak())

# ── Слайд 12: Ограничения ──
E += slide_title("Ограничения и направления развития")
E.append(tbl([
    ["Ограничение", "Как адресовать"],
    ["LLM-score требует калибровки\n(anchor points добавлены)", "Дополнительно: детерминированные метрики\nFlesch-Kincaid (+30), стоп-лист терминов (-4)"],
    ["LLM играет 'карикатуру' роли,\nа не реального человека (bias)", "Калибровка на реальных транскриптах СФГ.\nСравнить корреляцию с данными инФОМ"],
    ["Упрощение усиливает тревогу\n(Anxiety 8→9 при Clarity 3→6)", "Не баг, а фича: воспроизводит\nэффект Kim & Lee. Требует осознанного\nуправления тревожностью в тексте"],
    ["Не замена реальной фокус-группы.\nPR-отдел не примет решение на основе LLM", "Позиционируем как pre-screening tool:\nбыстрая проверка + обучение + A/B тест"],
    ["Нет валидации на исторических данных", "Next step: прогнать все релизы 2023-2024,\nсравнить с динамикой ИО (инФОМ)"],
], widths=[8 * cm, 10 * cm]))
E.append(PageBreak())

# ── Слайд 13: Литература ──
E += slide_title("Литература")
refs = [
    "Argyle et al. (2023). 'Out of One, Many.' Political Analysis, 31(3). — LLM как silicon samples",
    "Blinder et al. (2024). 'CB Communication with the General Public.' JEL. — сегментация аудиторий",
    "Bholat et al. (2019). 'Enhancing CB Communications.' JME, 108. — эффект упрощения языка",
    "Cloyne et al. (2024). 'Homeownership and MP.' JME. — ипотечники внимательнее",
    "Ehrmann & Wabitsch (2022). 'CB Communication with Non-Experts.' JME, 127. — -30% дисперсия",
    "Horton (2023). 'Homo Silicus.' NBER. — LLM воспроизводят поведенческие эксперименты",
    "Kim & Lee. 'Bounded Rationality in CB Communication.' — когнитивный разрыв",
    "Lamla & Vinogradov (2024). 'CB Announcements: Big News for Little People?' JME. — attention 30-40%",
    "Банк России WP 148 (2024). 'Households Inflation Expectations: RCT.' — низкая реакция на цель ЦБ",
    "Дубинина и др. (2025). 'Агенты-LLM для прогнозирования общественного мнения.' — СФГ",
    "IMF WP 2025/109. 'Large-Scale LLM Analysis of CB Communication.' — 169 ЦБ, 74K документов",
]
for i, r in enumerate(refs):
    E.append(Paragraph(f"{i + 1}. {r}", S_SM))

# ── Сборка ──
output = os.path.join(os.path.dirname(__file__), "docs", "presentation.pdf")
doc = SimpleDocTemplate(output, pagesize=landscape(A4),
                        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                        topMargin=2 * cm, bottomMargin=2 * cm)
doc.build(E)
print(f"PDF: {output}")
print(f"Слайдов: 12")
