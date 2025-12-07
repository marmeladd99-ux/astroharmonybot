import os
import logging
import asyncio
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask приложение
app = Flask(__name__)

# Получаем токен из переменных окружения
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

# Создаем бота и приложение БЕЗ updater
bot = Bot(token=TOKEN)
application = (
    Application.builder()
    .token(TOKEN)
    .updater(None)  # Отключаем updater для webhook
    .build()
)

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Я бот на Render через webhook! 🚀')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Доступные команды:\n/start - начать\n/help - помощь')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'Вы написали: {update.message.text}')

# Добавляем обработчики
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# Инициализация приложения при старте
async def initialize_app():
    await application.initialize()
    await application.start()
    logger.info("Application initialized and started")

# Запускаем инициализацию
asyncio.run(initialize_app())

# Flask маршруты
@app.route('/')
def index():
    return 'Telegram Bot is running! ✅'

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработка входящих обновлений от Telegram"""
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        asyncio.run(application.process_update(update))
        return 'ok', 200
    except Exception as e:
        logger.error(f'Error processing update: {e}')
        return 'error', 500

@app.route('/set_webhook')
def set_webhook():
    """Установка webhook"""
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        asyncio.run(bot.set_webhook(url=webhook_url))
        return f'Webhook set to {webhook_url}', 200
    except Exception as e:
        logger.error(f'Error setting webhook: {e}')
        return f'Error: {str(e)}', 500

@app.route('/webhook_info')
def webhook_info():
    """Проверка статуса webhook"""
    try:
        info = asyncio.run(bot.get_webhook_info())
        return {
            'url': info.url,
            'pending_update_count': info.pending_update_count,
            'last_error_date': str(info.last_error_date) if info.last_error_date else None,
            'last_error_message': info.last_error_message
        }, 200
    except Exception as e:
        logger.error(f'Error getting webhook info: {e}')
        return f'Error: {str(e)}', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
