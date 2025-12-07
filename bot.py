import os
import logging
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
PORT = int(os.environ.get('PORT', 10000))  # Render использует 10000 по умолчанию

logger.info(f"Starting bot with PORT={PORT}, WEBHOOK_URL={WEBHOOK_URL}")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set!")

# Создаем бота
bot = Bot(token=TOKEN)

# Глобальная переменная для application
application = None

def get_application():
    """Ленивая инициализация application"""
    global application
    if application is None:
        application = (
            Application.builder()
            .token(TOKEN)
            .updater(None)
            .build()
        )
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Инициализируем синхронно
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(application.initialize())
            loop.run_until_complete(application.start())
            logger.info("Application initialized and started")
        except Exception as e:
            logger.error(f"Error initializing application: {e}")
            raise
    
    return application

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Я бот на Render через webhook! 🚀')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Доступные команды:\n/start - начать\n/help - помощь')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'Вы написали: {update.message.text}')

# Flask маршруты
@app.route('/')
def index():
    return 'Telegram Bot is running! ✅', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработка входящих обновлений от Telegram"""
    try:
        app_instance = get_application()
        update = Update.de_json(request.get_json(force=True), bot)
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app_instance.process_update(update))
        loop.close()
        
        return 'ok', 200
    except Exception as e:
        logger.error(f'Error processing update: {e}', exc_info=True)
        return 'error', 500

@app.route('/set_webhook')
def set_webhook():
    """Установка webhook"""
    try:
        if not WEBHOOK_URL:
            return 'WEBHOOK_URL not set', 500
            
        webhook_url = f"{WEBHOOK_URL}/webhook"
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(bot.set_webhook(url=webhook_url))
        loop.close()
        
        logger.info(f'Webhook set to {webhook_url}')
        return f'Webhook set to {webhook_url}. Result: {result}', 200
    except Exception as e:
        logger.error(f'Error setting webhook: {e}', exc_info=True)
        return f'Error: {str(e)}', 500

@app.route('/webhook_info')
def webhook_info():
    """Проверка статуса webhook"""
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        info = loop.run_until_complete(bot.get_webhook_info())
        loop.close()
        
        return {
            'url': info.url,
            'pending_update_count': info.pending_update_count,
            'last_error_date': str(info.last_error_date) if info.last_error_date else None,
            'last_error_message': info.last_error_message
        }, 200
    except Exception as e:
        logger.error(f'Error getting webhook info: {e}', exc_info=True)
        return f'Error: {str(e)}', 500

if __name__ == '__main__':
    logger.info(f"Starting Flask app on 0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
