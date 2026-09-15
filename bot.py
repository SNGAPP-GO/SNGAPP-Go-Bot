from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN
import re

SNGAPP_URL = "https://t.me/sngapp_bot/app"

CITY_ALIASES = {
    "оренбург": "Оренбург", "оренбурга": "Оренбург", "оренбурге": "Оренбург",
    "орск": "Орск", "орска": "Орск", "орске": "Орск",
    "ясный": "Ясный", "ясного": "Ясный", "ясном": "Ясный",
    "казань": "Казань", "казани": "Казань",
    "чебоксары": "Чебоксары", "чебоксар": "Чебоксары", "чебоксарах": "Чебоксары",
    "краснодар": "Краснодар", "краснодара": "Краснодар", "краснодаре": "Краснодар",
    "сочи": "Сочи",
    "симферополь": "Симферополь", "симферополя": "Симферополь", "симферополе": "Симферополь",
    "севастополь": "Севастополь", "севастополя": "Севастополь", "севастополе": "Севастополь",
    "ялта": "Ялта", "ялты": "Ялта", "ялте": "Ялта",
    "керчь": "Керчь", "керчи": "Керчь",
    "феодосия": "Феодосия", "феодосии": "Феодосия",
    "судак": "Судак", "судака": "Судак", "судаке": "Судак",
    "джанкой": "Джанкой", "джанкоя": "Джанкой",
    "москва": "Москва", "москвы": "Москва", "москве": "Москва",
    "уфа": "Уфа", "уфы": "Уфа", "уфе": "Уфа",
    "нижний новгород": "Нижний Новгород", "нижнего новгорода": "Нижний Новгород",
    "владимир": "Владимир", "владимира": "Владимир",
    "елабуга": "Елабуга", "елабуги": "Елабуга",
    "набережные челны": "Набережные Челны", "набережных челнов": "Набережные Челны",
    "н.челны": "Набережные Челны", "н челны": "Набережные Челны",
    "курган": "Курган", "кургана": "Курган",
    "тюмень": "Тюмень", "тюмени": "Тюмень",
    "челябинск": "Челябинск", "челябинска": "Челябинск",
    "екатеринбург": "Екатеринбург", "екатеринбурга": "Екатеринбург",
    "владивосток": "Владивосток", "владивостока": "Владивосток",
    "уссурийск": "Уссурийск", "уссурийска": "Уссурийск",
    "находка": "Находка", "находки": "Находка",
    "арсеньев": "Арсеньев", "арсеньева": "Арсеньев",
    "большой камень": "Большой Камень", "большого камня": "Большой Камень",
    "ростов-на-дону": "Ростов-на-Дону", "ростова-на-дону": "Ростов-на-Дону",
    "ростов на дону": "Ростов-на-Дону", "ростова на дону": "Ростов-на-Дону",
    "майкоп": "Майкоп", "майкопа": "Майкоп",
    "пятигорск": "Пятигорск", "пятигорска": "Пятигорск",
    "минеральные воды": "Минеральные Воды", "минводы": "Минеральные Воды", "минвод": "Минеральные Воды",
    "астрахань": "Астрахань", "астрахани": "Астрахань",
}

NUMBER_WORDS = {
    "один": "1", "одна": "1", "одно": "1",
    "два": "2", "две": "2", "три": "3", "четыре": "4",
    "пять": "5", "шесть": "6", "семь": "7", "восемь": "8",
}


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


def normalize_text(text):
    return re.sub(r"[ \t]+", " ", text.replace("—", "-").replace("–", "-")).strip()


def normalize_city(value):
    value = re.sub(r"\s+", " ", value.strip(" ,.;:"))
    return CITY_ALIASES.get(value.lower(), " ".join(w.capitalize() for w in value.split()))


def detect_type(text):
    t = text.lower()

    carrier_markers = [
        "расписание поездок", "работаем каждый день", "ежедневно",
        "кассовые аппараты", "официальные", "электронные билеты",
        "отчетные документы", "мест всегда достаточно"
    ]
    carrier_score = sum(x in t for x in carrier_markers)

    driver_markers = [
        "#водитель", "еду ", "поеду ", "выезжаю", "есть места", "есть место",
        "возьму попутчиков", "возьму пассажиров", "могу взять",
        "свободные места", "минивэн", "микроавтобус"
    ]
    passenger_markers = [
        "#пассажир", "ищу машину", "ищем машину", "кто едет",
        "нужно уехать", "ищу попутку", "пассажир",
        "кто-нибудь едет", "кто нибудь едет"
    ]

    driver_score = sum(x in t for x in driver_markers)
    passenger_score = sum(x in t for x in passenger_markers)

    if re.search(r'\bкто(?:\s+|-)?(?:нибудь\s+)?едет\b', t):
        passenger_score += 2

    if carrier_score >= 2:
        return "🚐 Перевозчик"
    if driver_score > passenger_score and driver_score > 0:
        return "🚗 Водитель"
    if passenger_score > driver_score and passenger_score > 0:
        return "🙋 Пассажир"
    return "❓ Не определено"


def normalize_phone_key(raw):
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return "7" + digits[1:]
    return digits


def extract_phone(text):
    # Поддерживает +7/8, скобки, пробелы, дефисы, 3- и 4-значные коды.
    candidates = re.findall(
        r'(?<!\d)(?:\+7|8)(?:[\s\-()]|\d){9,18}(?!\d)',
        text
    )

    seen = set()
    result = []

    for raw in candidates:
        key = normalize_phone_key(raw)
        # Российский номер должен давать 11 цифр после нормализации.
        if len(key) != 11 or not key.startswith("7"):
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(re.sub(r"\s+", " ", raw).strip())

    return ", ".join(result[:4]) if result else "—"


def date_spans(text):
    spans = []

    for m in re.finditer(r'(?<!\d)(\d{1,2})\s*([./,])\s*(\d{1,2})\s*\2\s*(\d{2,4})(?!\d)', text):
        d, mo = int(m.group(1)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            spans.append((m.start(), m.end()))

    for m in re.finditer(r'(?<!\d)(\d{1,2})\s*([./])\s*(\d{1,2})(?![\d./])', text):
        d, mo = int(m.group(1)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            prefix = text[max(0, m.start()-8):m.start()].lower()
            if m.start() == 0 or text[m.start()-1] == "\n" or "дата" in prefix:
                spans.append((m.start(), m.end()))

    return spans


def extract_times(text):
    spans = date_spans(text)
    result = []

    for m in re.finditer(r'(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?!\d)', text):
        if any(m.start() < e and m.end() > s for s, e in spans):
            continue

        h, minute = re.split(r'[:.]', m.group(0))
        value = f"{int(h):02d}:{minute}"
        if value not in result:
            result.append(value)

    return result[:12]


def extract_dates(text):
    result = []
    low = text.lower()

    for word in ("сегодня", "завтра", "послезавтра"):
        if re.search(rf'\b{word}\b', low):
            result.append(word)

    for m in re.finditer(r'(?<!\d)(\d{1,2})\s*([./,])\s*(\d{1,2})\s*\2\s*(\d{2,4})(?!\d)', text):
        d, mo, y = int(m.group(1)), int(m.group(3)), m.group(4)
        if 1 <= d <= 31 and 1 <= mo <= 12:
            val = f"{d:02d}.{mo:02d}.{y}"
            if val not in result:
                result.append(val)

    for m in re.finditer(r'(?<!\d)(\d{1,2})\s*([./])\s*(\d{1,2})(?![\d./])', text):
        d, mo = int(m.group(1)), int(m.group(3))
        if not (1 <= d <= 31 and 1 <= mo <= 12):
            continue

        prefix = text[max(0, m.start()-8):m.start()].lower()
        if m.start() == 0 or text[m.start()-1] == "\n" or "дата" in prefix:
            val = f"{d:02d}.{mo:02d}"
            if val not in result:
                result.append(val)

    return result


def extract_seats(text):
    patterns = [
        r'(\d+)\s*(?:места|мест|место)\b',
        r'возьму\s*(\d+)(?:\s*-\s*(\d+))?\s*(?:попутчиков|пассажиров)?',
        r'до\s*(\d+)\s*(?:человек|пассажиров)',
    ]

    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            if len(m.groups()) >= 2 and m.group(2):
                return f"{m.group(1)}–{m.group(2)}"
            return m.group(1)

    words = "|".join(NUMBER_WORDS.keys())
    m = re.search(rf'\b(?:есть\s+)?({words})\s+(?:места|мест|место)\b', text, flags=re.I)
    return NUMBER_WORDS[m.group(1).lower()] if m else "—"


def extract_price(text):
    for p in [
        r'(?<!\d)(\d{2,5})\s*(?:₽|руб(?:лей|ля|\.|)?|р\b)',
        r'\bпо\s*(\d{2,5})\s*(?:₽|р|руб)?\b'
    ]:
        m = re.search(p, text, flags=re.I)
        if m:
            return f"{m.group(1)} ₽"
    return "—"


def find_known_cities(text):
    low = text.lower()
    matches = []

    for alias in sorted(CITY_ALIASES, key=len, reverse=True):
        for m in re.finditer(rf'(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])', low):
            matches.append((m.start(), m.end(), CITY_ALIASES[alias]))

    matches.sort(key=lambda x: (x[0], -(x[1]-x[0])))

    out, last_end = [], -1
    for item in matches:
        if item[0] >= last_end:
            out.append(item)
            last_end = item[1]

    return out


def extract_routes(text):
    t = normalize_text(text)
    routes = []

    for m in re.finditer(
        r'\b(?:с|из)\s+([А-ЯЁA-Z][А-Яа-яЁёA-Za-z.\- ]{1,35}?)\s+в\s+'
        r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z.\- ]{1,35}?)(?=\s+в\s+\d{1,2}[.:]\d{2}|[,.;:\n]|$)',
        t, flags=re.I
    ):
        a, b = normalize_city(m.group(1)), normalize_city(m.group(2))
        route = f"{a.upper()} → {b.upper()}"
        if route not in routes:
            routes.append(route)

    cities = find_known_cities(t)
    for i in range(len(cities)-1):
        a, b = cities[i], cities[i+1]
        between = t[a[1]:b[0]]
        if re.fullmatch(r'\s*(?:-|→|->|=>)\s*', between):
            route = f"{a[2].upper()} → {b[2].upper()}"
            if route not in routes:
                routes.append(route)

    return routes[:8]


def extract_time_ranges(text):
    result = []

    for m in re.finditer(
        r'(?<!\d)((?:[01]?\d|2[0-3])[:.][0-5]\d)\s*-\s*((?:[01]?\d|2[0-3])[:.][0-5]\d)(?!\d)',
        text
    ):
        a = m.group(1).replace(".", ":")
        b = m.group(2).replace(".", ":")
        ah, am = a.split(":")
        bh, bm = b.split(":")
        value = f"{int(ah):02d}:{am}-{int(bh):02d}:{bm}"
        if value not in result:
            result.append(value)

    return result


def extract_carrier_schedule(text):
    """
    Для регулярных перевозчиков:
    - игнорирует рекламный список маршрутов без расписания;
    - берет секции "Из X в Y", "Обратно из X в Y";
    - берет маршруты вида "Ясный-Москва (пятница, суббота)";
    - объединяет дубли и времена.
    """
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    entries = []

    current_route = None
    current_days = None
    current_times = []

    def flush():
        nonlocal current_route, current_days, current_times
        if current_route:
            entries.append({
                "route": current_route,
                "days": current_days or "ежедневно",
                "times": list(dict.fromkeys(current_times)),
            })
        current_route = None
        current_days = None
        current_times = []

    for line in lines:
        clean = normalize_text(line)

        # "Из Орска в Ясный:"
        m = re.search(
            r'^\s*из\s+([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]+?)\s+в\s+'
            r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]+?)\s*:?\s*$',
            clean, flags=re.I
        )
        if m:
            flush()
            current_route = f"{normalize_city(m.group(1)).upper()} → {normalize_city(m.group(2)).upper()}"
            current_days = "ежедневно"
            continue

        # "Обратно из Ясного в Орск:"
        m = re.search(
            r'^\s*обратно\s+из\s+([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]+?)\s+в\s+'
            r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]+?)\s*:?\s*$',
            clean, flags=re.I
        )
        if m:
            flush()
            current_route = f"{normalize_city(m.group(1)).upper()} → {normalize_city(m.group(2)).upper()}"
            current_days = "ежедневно"
            continue

        # "Ясный-Москва (пятница,суббота)"
        cities = find_known_cities(clean)
        if len(cities) >= 2:
            a, b = cities[0], cities[1]
            between = clean[a[1]:b[0]]

            dm = re.search(r'\(([^)]+)\)', clean)
            if re.fullmatch(r'\s*(?:-|→|->|=>)\s*', between) and dm:
                flush()
                current_route = f"{a[2].upper()} → {b[2].upper()}"
                current_days = dm.group(1).strip()
                current_times.extend(extract_time_ranges(clean))
                continue

        # Времена относятся к текущей секции.
        if current_route:
            for time_range in extract_time_ranges(clean):
                if time_range not in current_times:
                    current_times.append(time_range)

    flush()

    # Объединяем дубли одного и того же маршрута + режима дней.
    merged = {}
    order = []

    for entry in entries:
        key = (entry["route"], entry["days"])
        if key not in merged:
            merged[key] = {
                "route": entry["route"],
                "days": entry["days"],
                "times": [],
            }
            order.append(key)

        for value in entry["times"]:
            if value not in merged[key]["times"]:
                merged[key]["times"].append(value)

    return [merged[key] for key in order][:8]


def format_carrier_schedule(entries):
    if not entries:
        return "—"

    blocks = []
    for e in entries:
        times = ", ".join(e["times"]) if e["times"] else "время не указано"
        blocks.append(f"{e['route']}\n{e['days']}: {times}")

    return "\n\n".join(blocks)


def format_route_time_pairs(routes, times):
    if not routes:
        return "—"

    lines = []
    for i, route in enumerate(routes):
        lines.append(f"{route} — {times[i]}" if i < len(times) else route)

    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚘 SNGAPP Go\n\nДля теста просто перешлите мне объявление о поездке из Telegram-группы.",
        reply_markup=main_menu()
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Перешлите реальный пост из @ChedKazan или @blablacar_56.")


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Создать поездку в SNGAPP", url=SNGAPP_URL)]
    ])
    await update.message.reply_text("🚗 Создайте поездку в SNGAPP.", reply_markup=kb)


async def carriers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚐 Здесь появится каталог регулярных перевозчиков.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Для теста можно просто переслать или вставить текст объявления.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "search":
        await q.message.reply_text("🔎 Перешлите объявление из @ChedKazan или @blablacar_56.")
    elif q.data == "create":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Создать поездку в SNGAPP", url=SNGAPP_URL)]
        ])
        await q.message.reply_text("🚗 Создайте поездку в SNGAPP.", reply_markup=kb)
    elif q.data == "carriers":
        await q.message.reply_text("🚐 Здесь появится каталог перевозчиков.")
    else:
        await q.message.reply_text("ℹ️ Просто перешлите объявление о поездке.")


async def parse_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption or ""
    if not text:
        await update.message.reply_text("Не вижу текста объявления.")
        return

    kind = detect_type(text)

    if kind == "🚐 Перевозчик":
        schedule = extract_carrier_schedule(text)

        result = (
            "🧪 Результат разбора\n\n"
            f"Тип: {kind}\n\n"
            f"Маршруты и расписание:\n{format_carrier_schedule(schedule)}\n\n"
            f"Телефон: {extract_phone(text)}\n"
            f"Цена: {extract_price(text)}\n"
            f"Места: {extract_seats(text)}\n\n"
            "📄 Исходный текст: большой рекламный пост, сохранён для дальнейшей обработки."
        )
    else:
        routes = extract_routes(text)
        times = extract_times(text)
        dates = extract_dates(text)

        result = (
            "🧪 Результат разбора\n\n"
            f"Тип: {kind}\n"
            f"Маршруты:\n{format_route_time_pairs(routes, times)}\n"
            f"Дата: {', '.join(dates) if dates else '—'}\n"
            f"Места: {extract_seats(text)}\n"
            f"Цена: {extract_price(text)}\n"
            f"Телефон: {extract_phone(text)}\n\n"
            "📄 Исходный текст:\n" + text[:1200]
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
