import os
import re
import json
import hashlib
import psycopg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import BOT_TOKEN

DATABASE_URL = os.getenv("DATABASE_URL")
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


def db_connect():
    if not DATABASE_URL:
        raise RuntimeError("Переменная DATABASE_URL не задана")
    return psycopg.connect(DATABASE_URL)


def init_db():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rides (
                    id BIGSERIAL PRIMARY KEY,
                    content_hash TEXT UNIQUE NOT NULL,
                    telegram_message_id BIGINT,
                    telegram_chat_id BIGINT,
                    ride_type TEXT NOT NULL,
                    routes JSONB NOT NULL DEFAULT '[]'::jsonb,
                    dates JSONB NOT NULL DEFAULT '[]'::jsonb,
                    times JSONB NOT NULL DEFAULT '[]'::jsonb,
                    schedule JSONB NOT NULL DEFAULT '[]'::jsonb,
                    seats TEXT,
                    price TEXT,
                    phone TEXT,
                    raw_text TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS rides_created_at_idx
                ON rides(created_at DESC);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS rides_ride_type_idx
                ON rides(ride_type);
            """)
        conn.commit()


def save_ride(message, parsed):
    fingerprint = hashlib.sha256(
        re.sub(r"\s+", " ", parsed["raw_text"].strip().lower()).encode("utf-8")
    ).hexdigest()

    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO rides (
                    content_hash,
                    telegram_message_id,
                    telegram_chat_id,
                    ride_type,
                    routes,
                    dates,
                    times,
                    schedule,
                    seats,
                    price,
                    phone,
                    raw_text
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                    %s, %s, %s, %s
                )
                ON CONFLICT (content_hash)
                DO UPDATE SET created_at = rides.created_at
                RETURNING id, (xmax = 0) AS inserted;
            """, (
                fingerprint,
                message.message_id,
                message.chat_id,
                parsed["kind"],
                json.dumps(parsed["routes"], ensure_ascii=False),
                json.dumps(parsed["dates"], ensure_ascii=False),
                json.dumps(parsed["times"], ensure_ascii=False),
                json.dumps(parsed["schedule"], ensure_ascii=False),
                parsed["seats"],
                parsed["price"],
                parsed["phone"],
                parsed["raw_text"],
            ))
            ride_id, inserted = cur.fetchone()
        conn.commit()

    return ride_id, inserted


def latest_rides(limit=10):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, ride_type, routes, dates, times, seats, price
                FROM rides
                WHERE ride_type IN ('🚗 Водитель', '🚐 Перевозчик')
                ORDER BY created_at DESC
                LIMIT %s;
            """, (limit,))
            return cur.fetchall()


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
    candidates = re.findall(
        r'(?<!\d)(?:\+7|8)(?:[\s\-()]|\d){9,18}(?!\d)',
        text
    )

    seen = set()
    result = []

    for raw in candidates:
        key = normalize_phone_key(raw)
        if len(key) != 11 or not key.startswith("7"):
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(re.sub(r"\s+", " ", raw).strip())

    return ", ".join(result[:4]) if result else "—"


def date_spans(text):
    spans = []

    for m in re.finditer(
        r'(?<!\d)(\d{1,2})\s*([./,])\s*(\d{1,2})\s*\2\s*(\d{2,4})(?!\d)',
        text
    ):
        d, mo = int(m.group(1)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            spans.append((m.start(), m.end()))

    for m in re.finditer(
        r'(?<!\d)(\d{1,2})\s*([./])\s*(\d{1,2})(?![\d./])',
        text
    ):
        d, mo = int(m.group(1)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            prefix = text[max(0, m.start()-8):m.start()].lower()
            at_line_start = m.start() == 0 or text[m.start()-1] == "\n"
            if at_line_start or "дата" in prefix:
                spans.append((m.start(), m.end()))

    return spans


def extract_times(text):
    spans = date_spans(text)
    result = []

    for m in re.finditer(r'(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?!\d)', text):
        if any(m.start() < end and m.end() > start for start, end in spans):
            continue

        hour, minute = re.split(r'[:.]', m.group(0))
        value = f"{int(hour):02d}:{minute}"
        if value not in result:
            result.append(value)

    return result[:12]


def extract_dates(text):
    result = []
    t = text.lower()

    for word in ("сегодня", "завтра", "послезавтра"):
        if re.search(rf'\b{word}\b', t):
            result.append(word)

    for m in re.finditer(
        r'(?<!\d)(\d{1,2})\s*([./,])\s*(\d{1,2})\s*\2\s*(\d{2,4})(?!\d)',
        text
    ):
        d, mo, year = int(m.group(1)), int(m.group(3)), m.group(4)
        if 1 <= d <= 31 and 1 <= mo <= 12:
            value = f"{d:02d}.{mo:02d}.{year}"
            if value not in result:
                result.append(value)

    for m in re.finditer(
        r'(?<!\d)(\d{1,2})\s*([./])\s*(\d{1,2})(?![\d./])',
        text
    ):
        d, mo = int(m.group(1)), int(m.group(3))
        if not (1 <= d <= 31 and 1 <= mo <= 12):
            continue

        prefix = text[max(0, m.start()-8):m.start()].lower()
        at_line_start = m.start() == 0 or text[m.start()-1] == "\n"

        if at_line_start or "дата" in prefix:
            value = f"{d:02d}.{mo:02d}"
            if value not in result:
                result.append(value)

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
    m = re.search(
        rf'\b(?:есть\s+)?({words})\s+(?:места|мест|место)\b',
        text,
        flags=re.I
    )
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
        for m in re.finditer(
            rf'(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])',
            low
        ):
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
        t,
        flags=re.I
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
        r'(?<!\d)((?:[01]?\d|2[0-3])[:.][0-5]\d)\s*-\s*'
        r'((?:[01]?\d|2[0-3])[:.][0-5]\d)(?!\d)',
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

        m = re.search(
            r'^\s*из\s+([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]+?)\s+в\s+'
            r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]+?)\s*:?\s*$',
            clean,
            flags=re.I
        )
        if m:
            flush()
            current_route = (
                f"{normalize_city(m.group(1)).upper()} → "
                f"{normalize_city(m.group(2)).upper()}"
            )
            current_days = "ежедневно"
            continue

        m = re.search(
            r'^\s*обратно\s+из\s+([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]+?)\s+в\s+'
            r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]+?)\s*:?\s*$',
            clean,
            flags=re.I
        )
        if m:
            flush()
            current_route = (
                f"{normalize_city(m.group(1)).upper()} → "
                f"{normalize_city(m.group(2)).upper()}"
            )
            current_days = "ежедневно"
            continue

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

        if current_route:
            for time_range in extract_time_ranges(clean):
                if time_range not in current_times:
                    current_times.append(time_range)

    flush()

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


def parse_payload(text):
    kind = detect_type(text)

    if kind == "🚐 Перевозчик":
        schedule = extract_carrier_schedule(text)
        routes = [x["route"] for x in schedule]
        dates = []
        times = []
    else:
        schedule = []
        routes = extract_routes(text)
        dates = extract_dates(text)
        times = extract_times(text)

    return {
        "kind": kind,
        "routes": routes,
        "dates": dates,
        "times": times,
        "schedule": schedule,
        "seats": extract_seats(text),
        "price": extract_price(text),
        "phone": extract_phone(text),
        "raw_text": text,
    }


def format_route_time_pairs(routes, times):
    if not routes:
        return "—"

    lines = []
    for i, route in enumerate(routes):
        lines.append(f"{route} — {times[i]}" if i < len(times) else route)

    return "\n".join(lines)


def format_carrier_schedule(entries):
    if not entries:
        return "—"

    blocks = []

    for e in entries:
        times = ", ".join(e["times"]) if e["times"] else "время не указано"
        blocks.append(f"{e['route']}\n{e['days']}: {times}")

    return "\n\n".join(blocks)


def format_search_row(row):
    ride_id, ride_type, routes, dates, times, seats, price = row

    route_text = " / ".join(routes) if routes else "Маршрут не распознан"
    date_text = ", ".join(dates) if dates else "дата не указана"
    time_text = ", ".join(times) if times else ""

    line = f"#{ride_id} {ride_type}\n{route_text}\n{date_text}"

    if time_text:
        line += f" · {time_text}"

    if seats and seats != "—":
        line += f"\nМеста: {seats}"

    if price and price != "—":
        line += f" · Цена: {price}"

    return line


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚘 SNGAPP Go\n\n"
        "Перешлите объявление — я разберу его и сохраню в каталог.\n"
        "Команда /search покажет последние поездки.",
        reply_markup=main_menu()
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = latest_rides(10)

    if not rows:
        await update.message.reply_text("🔎 Каталог пока пуст.")
        return

    text = (
        "🔎 Последние поездки в каталоге\n\n"
        + "\n\n".join(format_search_row(r) for r in rows)
    )

    await update.message.reply_text(text[:3900])


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
        "🚐 Перевозчики сохраняются в общий каталог. Используйте /search."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Перешлите или вставьте объявление — бот сохранит его в каталог.\n"
        "/search — показать последние поездки."
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "search":
        rows = latest_rides(10)

        if not rows:
            await q.message.reply_text("🔎 Каталог пока пуст.")
        else:
            text = (
                "🔎 Последние поездки в каталоге\n\n"
                + "\n\n".join(format_search_row(r) for r in rows)
            )
            await q.message.reply_text(text[:3900])

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
            "🚐 Перевозчики сохраняются в общий каталог. Используйте /search."
        )

    else:
        await q.message.reply_text(
            "ℹ️ Перешлите объявление — я сохраню его в каталог."
        )


async def parse_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption or ""

    if not text:
        await update.message.reply_text("Не вижу текста объявления.")
        return

    parsed = parse_payload(text)

    try:
        ride_id, inserted = save_ride(update.message, parsed)
    except Exception as e:
        await update.message.reply_text(
            "⚠️ Текст разобран, но сохранить его в базу не удалось.\n"
            f"Ошибка: {e}"
        )
        return

    if parsed["kind"] == "🚐 Перевозчик":
        details = (
            f"Маршруты и расписание:\n"
            f"{format_carrier_schedule(parsed['schedule'])}\n\n"
            f"Телефон: {parsed['phone']}\n"
            f"Цена: {parsed['price']}\n"
            f"Места: {parsed['seats']}"
        )
    else:
        details = (
            f"Маршруты:\n"
            f"{format_route_time_pairs(parsed['routes'], parsed['times'])}\n"
            f"Дата: {', '.join(parsed['dates']) if parsed['dates'] else '—'}\n"
            f"Места: {parsed['seats']}\n"
            f"Цена: {parsed['price']}\n"
            f"Телефон: {parsed['phone']}"
        )

    status = "✅ Сохранено в каталог" if inserted else "♻️ Такое объявление уже есть в каталоге"

    await update.message.reply_text(
        f"{status}\n\n"
        f"ID: #{ride_id}\n"
        f"Тип: {parsed['kind']}\n"
        f"{details}\n\n"
        "Запись доступна через /search."
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Переменная BOT_TOKEN не задана")

    if not DATABASE_URL:
        raise RuntimeError("Переменная DATABASE_URL не задана")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("create", create))
    app.add_handler(CommandHandler("carriers", carriers))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, parse_message))

    print("SNGAPP Go bot started with PostgreSQL catalog")
    app.run_polling()


if __name__ == "__main__":
    main()
