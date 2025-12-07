import os
import telebot

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Привет! Я бот совместимости, нумерологии и астрологии. Напиши дату рождения.")

@bot.message_handler(func=lambda m: True)
def all_msg(msg):
    bot.reply_to(msg, "Я скоро научусь считать совместимость ✨")

bot.polling(none_stop=True)
