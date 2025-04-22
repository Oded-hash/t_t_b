from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, Dispatcher

import requests
from bs4 import BeautifulSoup
from newspaper import Article
import google.generativeai as genai
import os
import asyncio

TOKEN = os.environ.get("telegram_token")
WEBHOOK_URL = os.environ.get("webhook_url")  # תקבע ב-Render כ-Environment Variable

app = Flask(__name__)
bot_app = ApplicationBuilder().token(TOKEN).build()

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

# Add handlers
bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return 'ok'

@app.route('/')
def index():
    return "Bot is running via webhook."

if __name__ == '__main__':
    # קבע את ה-Webhook כאשר האפליקציה עולה
    async def set_webhook():
        await bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook/{TOKEN}")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
