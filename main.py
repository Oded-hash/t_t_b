from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

import requests
from bs4 import BeautifulSoup
from newspaper import Article
import google.generativeai as genai
import os
import asyncio
import aiohttp
import re
import argparse

TOKEN = os.environ.get("telegram_token")
WEBHOOK_URL = os.environ.get("webhook_url")

app = Flask(__name__)
bot_app = None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    link_match = re.search(r'https?://\S+', user_message)
    if link_match:
        link = link_match.group(0)
        print(f"User sent: {link}")
        answer = await process_answer(link)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="לא זוהה קישור בהודעה.")

async def process_answer(url):
    content = ""
    try:
        article = Article(url)
        article.download()
        article.parse()
        content = article.text
    except Exception as e:
        print(f"Error processing with newspaper: {e}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            article_element = soup.find('article') or soup.find(class_='article__content') or soup.find('main')
            content = article_element.get_text(strip=True) if article_element else "לא נמצא תוכן עיקרי במאמר."
        except requests.exceptions.RequestException as e:
            content = f"שגיאה בגישה לדף האינטרנט: {e}"
        except Exception as e:
            content = f"שגיאה לא צפויה בעיבוד הדף: {e}"

    if not content:
        return "לא הצלחתי לחלץ תוכן מהקישור שסופק."

    genai.configure(api_key=os.environ.get("gemini_api_key"))
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    msg = f"בבקשה תסכם ותתרגם לעברית את הטקסט הבא: {content}"
    try:
        response = await model.generate_content_async(msg)
        return response.text
    except Exception as e:
        return f"שגיאה בתקשורת עם Gemini: {e}"

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
async def webhook():
    global bot_app
    print("==> Webhook called")
    try:
        json_data = request.get_json(force=True)
        print("==> Incoming JSON:", json_data)
        update = Update.de_json(json_data, bot_app.bot)
        await bot_app.process_update(update)
        return 'ok'
    except Exception as e:
        print("==> Error in webhook:", str(e))
        import traceback
        traceback.print_exc()
        return 'error', 500

@app.route('/')
def index():
    return "הבוט פועל דרך webhook."

async def initialize_bot(local: bool = False):
    global bot_app
    bot_app = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    await bot_app.initialize()
    if not local:
        try:
            await bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook/{TOKEN}")
            print("==> Webhook set successfully")
        except Exception as e:
            print(f"==> Error setting webhook: {e}")
    else:
        print("==> Running locally, webhook will not be set.")

@app.before_first_request
def before_first_request():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="Run the bot locally without webhook")
    args = parser.parse_args()
    asyncio.run(initialize_bot(local=args.local))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
