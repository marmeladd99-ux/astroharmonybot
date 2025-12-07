import os
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Функции бота
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Привет! Я бот совместимости, нумерологии и астрологии. Напиши дату рождения.")

@bot.message_handler(func=lambda m: True)
def all_msg(msg):
    bot.reply_to(msg, "Я скоро научусь считать совместимость ✨")

# Flask сервер
app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running!", 200

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=os.getenv("RENDER_EXTERNAL_URL") + "/" + TOKEN)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
