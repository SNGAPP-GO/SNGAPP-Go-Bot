from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🚘 SNGAPP Go\n\n"
        "Помогаю находить поездки и перевозчиков в одном месте.\n\n"
        "Выберите действие:"
    )
    await update.message.reply_text(text, reply_markup=main_menu())


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔎 Поиск поездки\n\n"
        "Скоро здесь будет поиск предложений водителей из подключённых Telegram-источников.\n\n"
        "Сейчас тестируем работу бота."
    )


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Создать поездку в SNGAPP", url=SNGAPP_URL)]
    ])
    await update.message.reply_text(
        "🚗 Хотите разместить свою поездку?\n\n"
        "Создайте её в SNGAPP — пассажиры смогут найти ваше предложение в одном месте.",
        reply_markup=keyboard,
    )


async def carriers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚐 Перевозчики\n\n"
        "Здесь появится каталог регулярных перевозчиков и их маршрутов."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Команды SNGAPP Go:\n\n"
        "/start — главное меню\n"
        "/search — найти поездку\n"
        "/create — создать поездку\n"
        "/carriers — перевозчики\n"
        "/help — помощь"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "search":
        text = (
            "🔎 Поиск поездки\n\n"
            "Скоро здесь будет поиск предложений водителей из подключённых Telegram-источников.\n\n"
            "Сейчас тестируем работу бота."
        )
        markup = None

    elif query.data == "create":
        text = (
            "🚗 Хотите разместить свою поездку?\n\n"
            "Создайте её в SNGAPP — пассажиры смогут найти ваше предложение в одном месте."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Создать поездку в SNGAPP", url=SNGAPP_URL)]
        ])

    elif query.data == "carriers":
        text = (
            "🚐 Перевозчики\n\n"
            "Здесь появится каталог регулярных перевозчиков и их маршрутов."
        )
        markup = None

    else:
        text = (
            "ℹ️ Команды SNGAPP Go:\n\n"
            "/start — главное меню\n"
            "/search — найти поездку\n"
            "/create — создать поездку\n"
            "/carriers — перевозчики\n"
            "/help — помощь"
        )
        markup = None

    await query.message.reply_text(text, reply_markup=markup)


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

    print("SNGAPP Go bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
