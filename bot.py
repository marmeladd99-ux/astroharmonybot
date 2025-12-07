import os
import logging
from datetime import datetime
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import asyncio
from threading import Thread

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
PORT = int(os.environ.get('PORT', 10000))

logger.info(f"Starting bot with PORT={PORT}, WEBHOOK_URL={WEBHOOK_URL}")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set!")

# Создаем настройки для HTTP запросов
request_instance = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=30.0,
    read_timeout=30.0,
    write_timeout=30.0,
    pool_timeout=30.0
)

# Создаем бота
bot = Bot(token=TOKEN, request=request_instance)

# Глобальная переменная для application
application = None
loop = None
loop_thread = None

def start_event_loop():
    """Запускает event loop в отдельном потоке"""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

def initialize_application():
    """Инициализация application"""
    global application, loop, loop_thread
    
    if application is None:
        # Запускаем event loop в отдельном потоке
        loop_thread = Thread(target=start_event_loop, daemon=True)
        loop_thread.start()
        
        # Ждём пока loop инициализируется
        import time
        time.sleep(0.5)
        
        # Создаём application
        application = (
            Application.builder()
            .token(TOKEN)
            .request(request_instance)
            .updater(None)
            .build()
        )
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("date", date_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Инициализируем application
        asyncio.run_coroutine_threadsafe(application.initialize(), loop).result()
        asyncio.run_coroutine_threadsafe(application.start(), loop).result()
        
        logger.info("Application initialized and started")
    
    return application

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.first_name}! 👋\n\n'
        f'Я AstroHarmony бот. Отправь мне сообщение, и я его повторю!\n\n'
        f'Команды:\n'
        f'/start - начать\n'
        f'/help - помощь\n'
        f'/date - показать текущую дату и время'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Доступные команды:\n\n'
        '/start - начать работу\n'
        '/help - показать это сообщение\n'
        '/date - показать текущую дату и время\n\n'
        'Просто напиши мне что-нибудь, и я отвечу!'
    )

async def date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущую дату и время"""
    now = datetime.now()
    
    # Форматируем дату
    date_str = now.strftime('%d.%m.%Y')
    time_str = now.strftime('%H:%M:%S')
    weekday = now.strftime('%A')
    
    # Переводим день недели на русский
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
    
    response = (
        f'📅 Сегодня: {weekday_ru}\n'
        f'📆 Дата: {date_str}\n'
        f'⏰ Время: {time_str}'
    )
    
    await update.message.reply_text(response)

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
        app_instance = initialize_application()
        update = Update.de_json(request.get_json(force=True), bot)
        
        # Выполняем в нашем event loop
        future = asyncio.run_coroutine_threadsafe(
            app_instance.process_update(update),
            loop
        )
        future.result(timeout=30)
        
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
        
        # Инициализируем application если ещё не инициализирован
        initialize_application()
        
        # Удаляем старый webhook
        future = asyncio.run_coroutine_threadsafe(
            bot.delete_webhook(drop_pending_updates=True),
            loop
        )
        future.result()
        
        # Устанавливаем новый
        future = asyncio.run_coroutine_threadsafe(
            bot.set_webhook(url=webhook_url),
            loop
        )
        result = future.result()
        
        logger.info(f'Webhook set to {webhook_url}')
        return f'Webhook set to {webhook_url}. Result: {result}', 200
    except Exception as e:
        logger.error(f'Error setting webhook: {e}', exc_info=True)
        return f'Error: {str(e)}', 500

@app.route('/webhook_info')
def webhook_info():
    """Проверка статуса webhook"""
    try:
        initialize_application()
        
        future = asyncio.run_coroutine_threadsafe(
            bot.get_webhook_info(),
            loop
        )
        info = future.result()
        
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
