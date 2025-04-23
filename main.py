from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

import requests
from bs4 import BeautifulSoup
from newspaper import Article
import google.generativeai as genai
import os
import asyncio

TOKEN = os.environ.get("telegram_token")
WEBHOOK_URL = os.environ.get("webhook_url")  # תקבע ב-Render כ-Environment Variable

app = Flask(__name__)

# פונקציה לאתחול ה-bot
async def initialize_bot():
    bot_app = ApplicationBuilder().token(TOKEN).build()
    # כאן נוסיף את ה-handler
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # נוודא שה-bot מאותחל לפני שמבצעים את פעולת ה-webhook
    await bot_app.initialize()
    await bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook/{TOKEN}")
    print("==> Webhook set successfully")
    return bot_app


# Define handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    first = user_message.split("https:")[1:]
    link = 'https:' + first[0]
    print(f"User sent: {link}")

    answer = process_answer(link)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)

def process_answer(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        content = article.text
        title = article.title
    except Exception as e:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                article = soup.find('article') or soup.find(class_='article__content') or soup.find('main')
                content = article.get_text() if article else "Main article content not found."
                title = soup.title.string
            else:
                content = "Couldn't fetch the page."
        except Exception as e:
            content = f"An error occurred: {str(e)}"

    genai.configure(api_key=os.environ.get("gemini_api_key"))

    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    msg = f"pls summarize and translate to hebrew the next text: {content}"
    response = model.generate_content(msg)
    return response.text


@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    print("==> Webhook called")
    try:
        json_data = request.get_json(force=True)
        print("==> Incoming JSON:", json_data)

        update = Update.de_json(json_data, bot_app.bot)
        asyncio.run(bot_app.process_update(update))
        return 'ok'
    except Exception as e:
        print("==> Error in webhook:", str(e))
        import traceback
        traceback.print_exc()
        return 'error', 500

@app.route('/')
def index():
    return "Bot is running via webhook."


# === אתחול ה-bot ברקע ===
@app.before_first_request
def before_first_request():
    # אתחול הבוט ברקע
    loop = asyncio.get_event_loop()
    loop.create_task(initialize_bot())


# Run Flask app
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)
