import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup
from newspaper import Article
import google.generativeai as genai
import json
import asyncio

app = Flask(__name__)

TOKEN = os.environ["telegram_token"]
API_KEY = os.environ["gemini_api_key"]
application = None  # נאתחל אחר כך

# ========== Handlers ==========

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("השרת למעלה, תכף נתחיל לעבד את הבקשה שלך")
    try:
        user_message = update.message.text
        first = user_message.split("https:")[1:]
        link = 'https:' + first[0]
    except:
        await update.message.reply_text("הבקשה לא תקינה, בדוק את תוכן ההודעה ששלחת")
        return

    answer = process_answer(link)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)

def process_answer(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        content = article.text
    except Exception:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            article_tag = soup.find('article') or soup.find('main')
            content = article_tag.get_text() if article_tag else "לא נמצא תוכן"
        except Exception as e:
            return f"שגיאה: {str(e)}"

    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    prompt = f"Please summarize and translate to Hebrew the following text:\n{content}"
    response = model.generate_content(prompt)
    return response.text

# ========== Webhook route ==========

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    global application
    json_str = request.get_data().decode('UTF-8')
    update_data = json.loads(json_str)
    update = Update.de_json(update_data, application.bot)

    # דאג שה event loop פעיל
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # הרצת המשימה האסינכרונית
    loop.create_task(application.process_update(update))  # לא להשתמש ב- await כאן
    return 'OK'

# ========== Webhook setup ==========

def set_webhook():
    base_url = "https://t-t-b.onrender.com"
    webhook_url = f"{base_url}/{TOKEN}"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    print("Set webhook:", response.json())  # הדפסת תשובה מה־API של Telegram

# ========== Main ==========

async def main():
    # אתחול ה־Application בצורה אסינכרונית
    global application
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # אתחול האפליקציה בצורה אסינכרונית
    await application.initialize()

    set_webhook()
    print("Bot is running in webhook mode via Render")
    
    # הפעלת השרת
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)  # הפעלת debug mode

if __name__ == '__main__':
    asyncio.run(main())  # הפעל את כל התהליכים האסינכרוניים דרך asyncio.run
