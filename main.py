import os
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

async def respond_same_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    length = len(user_message)
    response = 'x' * length
    await update.message.reply_text(response)

async def main():
    application = Application.builder().token(os.environ["BOT_TOKEN"]).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond_same_length))
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
