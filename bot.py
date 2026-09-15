import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import BOT_TOKEN


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот SNGAPP-поездки работает!")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Переменная BOT_TOKEN не задана")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
