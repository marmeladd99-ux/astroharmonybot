import os
from flask import Flask, request
import telebot

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

server = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Привет! Я бот совместимости ✨ Напиши свою дату рождения.")

@bot.message_handler(func=lambda m: True)
def all_msg(msg):
    bot.reply_to(msg, "Я скоро научусь считать совместимость ✨")

# Flask маршрут для Telegram
@server.route('/' + TOKEN, methods=['POST'])
def telegram_webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

# Корневой маршрут (чтобы Render не выдавал Not Found)
@server.route('/')
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
