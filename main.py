import os
import json
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from bs4 import BeautifulSoup
from newspaper import Article

app = Flask(__name__)
TOKEN = os.environ.get("telegram_token")
API_KEY = os.environ.get("gemini_api_key")

application = ApplicationBuilder().token(TOKEN).build()

# ========== Handlers ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("השרת למעלה, תכף נתחיל לעבד את הבקשה שלך")

    try:
        user_message = update.message.text
        first = user_message.split("https:")[1:]
        link = 'https:' + first[0]
        print(f"User sent: {link}")
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

# ========== Webhook Flask route ==========
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json_str, application.bot)
    application.process_update(update)
    return 'OK'

# ========== Set webhook on startup ==========
def set_webhook():
    webhook_url = f"https://t-t-b.onrender.com{TOKEN}"  # Replace with your actual deployed URL
    print(webhook_url)
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    print(url)
    response = requests.get(url)
    print("Set webhook response:", response.json())

# ========== Main ==========
if __name__ == '__main__':
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    set_webhook()
    print("Bot is running in webhook mode...")
    app.run(host="0.0.0.0", port=5000)
