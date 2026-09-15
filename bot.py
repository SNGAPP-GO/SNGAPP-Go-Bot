from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN
import re

SNGAPP_URL = "https://t.me/sngapp_bot/app"


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔎 Найти поездку", callback_data="search"),
            InlineKeyboardButton("➕ Создать поездку", callback_data="create"),
        ],
        [
            InlineKeyboardButton("🚐 Перевозчики", callback_data="carriers"),
            InlineKeyboardButton("ℹ️ Помощь", callback_data="help"),
        ],
    ])


def normalize_text(text: str) -> str:
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def detect_type(text: str) -> str:
    t = text.lower()

    driver_markers = [
        "#водитель", "еду ", "поеду ", "выезжаю", "есть места",
        "возьму попутчиков", "возьму пассажиров", "могу взять",
        "свободные места", "минивэн", "микроавтобус"
    ]
    passenger_markers = [
        "#пассажир", "ищу машину", "ищем машину", "кто едет",
        "нужно уехать", "ищу попутку", "пассажир"
    ]

    driver_score = sum(marker in t for marker in driver_markers)
    passenger_score = sum(marker in t for marker in passenger_markers)

    if driver_score > passenger_score and driver_score > 0:
        return "🚗 Водитель"
    if passenger_score > driver_score and passenger_score > 0:
        return "🙋 Пассажир"
    return "❓ Не определено"


def extract_phone(text: str) -> str:
    found = re.findall(
        r'(?<!\d)(?:\+7|8)[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)',
        text
    )
    return ", ".join(found[:3]) if found else "—"


def extract_times(text: str) -> list[str]:
    # Время вида 9.30 / 09:30, но не часть даты.
    found = re.findall(r'(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?!\d)', text)
    result = []
    for item in found:
        normalized = item.replace(".", ":")
        if normalized not in result:
            result.append(normalized)
    return result[:8]


def extract_dates(text: str) -> list[str]:
    t = text.lower()
    result = []

    for word in ("сегодня", "завтра", "послезавтра"):
        if re.search(rf'\b{word}\b', t):
            result.append(word)

    # Дата 14.09 / 14. 09 / 14.09.2026 / 14/09
    for m in re.finditer(
        r'(?<!\d)(\d{1,2})\s*[./]\s*(\d{1,2})(?:\s*[./]\s*(\d{2,4}))?(?!\d)',
        text
    ):
        day = int(m.group(1))
        month = int(m.group(2))

        # Не принимаем 9.30 или 13.30 за дату.
        if not (1 <= day <= 31 and 1 <= month <= 12):
            continue

        year = m.group(3)
        value = f"{day:02d}.{month:02d}"
        if year:
            value += f".{year}"

        if value not in result:
            result.append(value)

    return result


def extract_seats(text: str) -> str:
    patterns = [
        r'(\d+)\s*(?:места|мест|место)\b',
        r'возьму\s*(\d+)(?:\s*-\s*(\d+))?\s*(?:попутчиков|пассажиров)?',
        r'до\s*(\d+)\s*(?:человек|пассажиров)',
    ]

    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            continue

        if len(m.groups()) >= 2 and m.group(2):
            return f"{m.group(1)}–{m.group(2)}"
        return m.group(1)

    return "—"


def extract_price(text: str) -> str:
    patterns = [
        r'(?<!\d)(\d{2,5})\s*(?:₽|руб(?:лей|ля|\.|)?|р\b)',
        r'\bпо\s*(\d{2,5})\s*(?:₽|р|руб)?\b',
    ]

    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return f"{m.group(1)} ₽"

    return "—"


def clean_city(value: str) -> str:
    value = value.strip(" ,.;:")
    value = re.sub(r'\s+', ' ', value)
    return value


def extract_routes(text: str) -> list[str]:
    t = normalize_text(text)
    routes = []

    # "с Оренбурга в Орск"
    # "из Краснодара в Крым"
    for m in re.finditer(
        r'\b(?:с|из)\s+([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]{2,30}?)\s+в\s+'
        r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]{2,30}?)(?=\s+в\s+\d{1,2}[.:]\d{2}|[,.;\n]|$)',
        t,
        flags=re.IGNORECASE
    ):
        origin = clean_city(m.group(1))
        destination = clean_city(m.group(2))
        route = f"{origin} → {destination}"
        if route not in routes:
            routes.append(route)

    # "обратно с Орска в Оренбург"
    for m in re.finditer(
        r'\bобратно\s+(?:с|из)\s+([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]{2,30}?)\s+в\s+'
        r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]{2,30}?)(?=\s+в\s+\d{1,2}[.:]\d{2}|[,.;\n]|$)',
        t,
        flags=re.IGNORECASE
    ):
        origin = clean_city(m.group(1))
        destination = clean_city(m.group(2))
        route = f"{origin} → {destination}"
        if route not in routes:
            routes.append(route)

    # "Казань - Чебоксары" / "Казань → Чебоксары"
    if not routes:
        for m in re.finditer(
            r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z.\- ]{1,30}?)\s*(?:→|->|=>|\s-\s)\s*'
            r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z.\- ]{1,30})(?=[,.;\n]|$)',
            t
        ):
            origin = clean_city(m.group(1))
            destination = clean_city(m.group(2))
            route = f"{origin} → {destination}"
            if route not in routes:
                routes.append(route)

    return routes[:4]


def format_route_time_pairs(routes: list[str], times: list[str]) -> str:
    if not routes:
        return "—"

    lines = []
    for i, route in enumerate(routes):
        if i < len(times):
            lines.append(f"{route} — {times[i]}")
        else:
            lines.append(route)
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚘 SNGAPP Go\n\n"
        "Для теста просто перешлите мне объявление о поездке из Telegram-группы.",
        reply_markup=main_menu(),
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔎 Перешлите реальный пост из @ChedKazan или @blablacar_56."
    )


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Создать поездку в SNGAPP", url=SNGAPP_URL)]
    ])
    await update.message.reply_text(
        "🚗 Создайте поездку в SNGAPP.",
        reply_markup=kb
    )


async def carriers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚐 Здесь появится каталог регулярных перевозчиков."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Для теста можно просто переслать или вставить текст объявления."
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "search":
        await q.message.reply_text(
            "🔎 Перешлите объявление из @ChedKazan или @blablacar_56."
        )
    elif q.data == "create":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Создать поездку в SNGAPP", url=SNGAPP_URL)]
        ])
        await q.message.reply_text(
            "🚗 Создайте поездку в SNGAPP.",
            reply_markup=kb
        )
    elif q.data == "carriers":
        await q.message.reply_text(
            "🚐 Здесь появится каталог перевозчиков."
        )
    else:
        await q.message.reply_text(
            "ℹ️ Просто перешлите объявление о поездке."
        )


async def parse_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption or ""
    if not text:
        await update.message.reply_text("Не вижу текста объявления.")
        return

    routes = extract_routes(text)
    times = extract_times(text)
    dates = extract_dates(text)

    result = (
        "🧪 Результат разбора\n\n"
        f"Тип: {detect_type(text)}\n"
        f"Маршруты:\n{format_route_time_pairs(routes, times)}\n"
        f"Дата: {', '.join(dates) if dates else '—'}\n"
        f"Места: {extract_seats(text)}\n"
        f"Цена: {extract_price(text)}\n"
        f"Телефон: {extract_phone(text)}\n\n"
        "📄 Исходный текст:\n"
        + text[:1800]
    )

    await update.message.reply_text(result)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Переменная BOT_TOKEN не задана")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("create", create))
    app.add_handler(CommandHandler("carriers", carriers))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, parse_message))

    print("SNGAPP Go bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
