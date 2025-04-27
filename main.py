import argparse
import os,json
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import requests
from bs4 import BeautifulSoup
from newspaper import Article
import google.generativeai as genai



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

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    msg = f"pls summarize and translate to hebrew the next text: {content}"
    response = model.generate_content(msg)
    return response.text

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("שלום! אני הבוט שלך 😄")



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="בוט טלגרם עם הודעות עליית/ירידת שרת")
    parser.add_argument("--local", action="store_true", help="run localy")
    args = parser.parse_args()
    if args.local:
        with open('keys.json', 'r') as file:
            data = json.load(file)
        TOKEN = data["telegram_token"]
        api_key=data["gemini_api_key"]
    else:
        TOKEN=os.environ.get("telegram_token")
        api_key=os.environ.get("gemini_api_key")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("server is up")
    app.run_polling()
