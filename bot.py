import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import asyncio
from threading import Thread

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен и URL из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # https://your-app.onrender.com

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

# Создаем Flask приложение
app = Flask(__name__)

# Создаем приложение бота
application = Application.builder().token(TOKEN).build()

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '👋 Привет! Я AstroHarmony бот.\n\n'
        'Отправь мне свою дату рождения в формате ДД.ММ.ГГГГ (например, 15.03.1990), '
        'и я расскажу о твоем знаке зодиака!'
    )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Простая проверка формата даты
    if len(user_message.split('.')) == 3:
        try:
            day, month, year = map(int, user_message.split('.'))
            
            # Определение знака зодиака
            zodiac_sign = get_zodiac_sign(day, month)
            
            response = f'🌟 Твой знак зодиака: {zodiac_sign}\n\n'
            response += 'Спасибо за использование AstroHarmony!'
            
            await update.message.reply_text(response)
        except ValueError:
            await update.message.reply_text(
                '❌ Неправильный формат даты.\n'
                'Пожалуйста, используй формат ДД.ММ.ГГГГ (например, 15.03.1990)'
            )
    else:
        await update.message.reply_text(
            '❌ Неправильный формат.\n'
            'Отправь дату рождения в формате ДД.ММ.ГГГГ (например, 15.03.1990)'
        )

def get_zodiac_sign(day: int, month: int) -> str:
    """Определяет знак зодиака по дате"""
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "♈ Овен"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "♉ Телец"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "♊ Близнецы"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "♋ Рак"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "♌ Лев"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "♍ Дева"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "♎ Весы"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "♏ Скорпион"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "♐ Стрелец"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "♑ Козерог"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "♒ Водолей"
    else:
        return "♓ Рыбы"

# Webhook endpoint
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Обработка входящих обновлений через webhook"""
    json_data = request.get_json()
    update = Update.de_json(json_data, application.bot)
    
    # Запускаем обработку в event loop
    asyncio.run(application.process_update(update))
    
    return 'ok'

@app.route('/')
def index():
    return 'Bot is running!'

@app.route('/health')
def health():
    return 'OK'

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Инициализация бота
def setup_webhook():
    """Настройка webhook"""
    asyncio.run(application.initialize())
    asyncio.run(application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}"))
    logger.info(f"Webhook set to {WEBHOOK_URL}/{TOKEN}")

if __name__ == '__main__':
    # Настраиваем webhook при запуске
    if WEBHOOK_URL:
        setup_webhook()
    
    # Запускаем Flask сервер
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
