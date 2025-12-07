import os
import logging
from datetime import datetime
from flask import Flask, request
import telebot

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask
app = Flask(__name__)

# Токен
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set!")

bot = telebot.TeleBot(TOKEN)

# ---------- Команды ----------

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "Привет! 👋\n"
        "Я AstroHarmony бот.\n\n"
        "Команды:\n"
        "/start – начать\n"
        "/help – помощь\n"
        "/date – сегодняшняя дата"
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(
        message,
        "Доступные команды:\n\n"
        "/start – начать\n"
        "/help – справка\n"
        "/date – показать сегодняшнюю дату\n"
    )

@bot.message_handler(commands=['date'])
def date_command(message):
    now = datetime.now()
    date_str = now.strftime('%d.%m.%Y')
    weekday = now.strftime('%A')
    weekdays_ru = {
        'Monday': 'Понедельник',
        'Tuesday': 'Вторник',
        'Wednesday': 'Среда',
        'Thursday': 'Четверг',
        'Friday': 'Пятница',
        'Saturday': 'Суббота',
        'Sunday': 'Воскресенье'
    }
    weekday_ru = weekdays_ru.get(weekday, weekday)

    bot.reply_to(
        message,
        f"📅 Сегодня: {weekday_ru}\n"
        f"📆 Дата: {date_str}"
    )

@bot.message_handler(content_types=['text'])
def echo(message):
    bot.reply_to(message, f"Вы написали: {message.text}")

# ---------- WEBHOOK ----------

@app.route('/', methods=['GET'])
def index():
    return "Telegram bot is running! ✅", 200

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    """Получение обновлений от Telegram"""
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Установка webhook вручную"""
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if not WEBHOOK_URL:
        return "WEBHOOK_URL not set", 500

    full_url = f"{WEBHOOK_URL}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=full_url)

    return f"Webhook установлен: {full_url}", 200


if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 10000))
    logger.info(f"Starting Flask app on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
