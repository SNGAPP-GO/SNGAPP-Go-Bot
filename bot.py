from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN
import re

SNGAPP_URL = "https://t.me/sngapp_bot/app"

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Найти поездку", callback_data="search"),
         InlineKeyboardButton("➕ Создать поездку", callback_data="create")],
        [InlineKeyboardButton("🚐 Перевозчики", callback_data="carriers"),
         InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ])

def detect_type(text):
    t = text.lower()
    d = sum(x in t for x in ["#водитель","еду ","поеду ","выезжаю","есть места","возьму попутчиков","могу взять","минивэн","микроавтобус"])
    p = sum(x in t for x in ["#пассажир","ищу машину","ищем машину","кто едет","нужно уехать","ищу попутку","пассажир"])
    if d > p and d > 0:
        return "🚗 Водитель"
    if p > d and p > 0:
        return "🙋 Пассажир"
    return "❓ Не определено"

def extract_phone(text):
    found = re.findall(r'(?:\+7|8)[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}', text)
    return ", ".join(found[:3]) if found else "—"

def extract_time(text):
    found = re.findall(r'(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?!\d)', text)
    return ", ".join(x.replace(".", ":") for x in found[:6]) if found else "—"

def extract_date(text):
    found = re.findall(r'(?<!\d)\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?(?!\d)', text)
    rel = re.findall(r'\b(?:сегодня|завтра|послезавтра)\b', text, flags=re.I)
    vals = list(dict.fromkeys(found + rel))
    return ", ".join(vals) if vals else "—"

def extract_seats(text):
    m = re.search(r'(\d+)\s*(?:места|мест|место)\b', text, flags=re.I)
    if m:
        return m.group(1)
    m = re.search(r'возьму\s*(\d+)(?:\s*-\s*(\d+))?', text, flags=re.I)
    if m:
        return f"{m.group(1)}–{m.group(2)}" if m.group(2) else m.group(1)
    return "—"

def extract_price(text):
    m = re.search(r'(?<!\d)(\d{2,5})\s*(?:₽|руб(?:лей|ля|\.|)?|р\b)', text, flags=re.I)
    return f"{m.group(1)} ₽" if m else "—"

def extract_route(text):
    s = text.replace("—","-").replace("–","-")
    m = re.search(r'([А-ЯЁA-Z][А-Яа-яЁёA-Za-z.\- ]{1,30})\s*(?:→|->|=>| - )\s*([А-ЯЁA-Z][А-Яа-яЁёA-Za-z.\- ]{1,30})', s)
    if m:
        return f"{m.group(1).strip()} → {m.group(2).strip()}"
    m = re.search(r'\bиз\s+([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]{2,25}?)\s+в\s+([А-ЯЁA-Z][А-Яа-яЁёA-Za-z\- ]{2,25})(?:[,.\n]|$)', text, flags=re.I)
    if m:
        return f"{m.group(1).strip()} → {m.group(2).strip()}"
    return "—"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚘 SNGAPP Go\n\nДля теста просто перешлите мне объявление о поездке из Telegram-группы.",
        reply_markup=main_menu()
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Перешлите реальный пост из @ChedKazan или @blablacar_56.")

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Создать поездку в SNGAPP", url=SNGAPP_URL)]])
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
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Создать поездку в SNGAPP", url=SNGAPP_URL)]])
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

    result = (
        "🧪 Результат разбора\n\n"
        f"Тип: {detect_type(text)}\n"
        f"Маршрут: {extract_route(text)}\n"
        f"Дата: {extract_date(text)}\n"
        f"Время: {extract_time(text)}\n"
        f"Места: {extract_seats(text)}\n"
        f"Цена: {extract_price(text)}\n"
        f"Телефон: {extract_phone(text)}\n\n"
        "📄 Исходный текст:\n" + text[:1800]
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
