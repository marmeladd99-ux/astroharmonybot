import os
import logging
import re
from datetime import datetime
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import httpx

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
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
PORT = int(os.environ.get('PORT', 10000))

logger.info(f"Starting bot with PORT={PORT}, WEBHOOK_URL={WEBHOOK_URL}")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set!")

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not set! Compatibility analysis will not work.")

# Создаем настройки для HTTP запросов с увеличенным pool
request_instance = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=30.0,
    read_timeout=30.0,
    write_timeout=30.0,
    pool_timeout=30.0
)

# Глобальная переменная для application
application = None
initialization_lock = False

# Словарь для хранения состояния пользователей
user_states = {}

def get_application():
    """Ленивая инициализация application"""
    global application, initialization_lock
    
    if application is None and not initialization_lock:
        initialization_lock = True
        try:
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
            application.add_handler(CommandHandler("compatibility", compatibility_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            # Инициализируем синхронно
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(application.initialize())
            loop.run_until_complete(application.start())
            logger.info("Application initialized and started")
        except Exception as e:
            logger.error(f"Error initializing application: {e}")
            initialization_lock = False
            raise
        finally:
            initialization_lock = False
    
    return application

def parse_date(text):
    """Парсинг даты из текста в различных форматах"""
    # Форматы: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
    patterns = [
        r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})',  # DD.MM.YYYY
        r'(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})',  # YYYY-MM-DD
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if len(groups[0]) == 4:  # YYYY-MM-DD format
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                else:  # DD.MM.YYYY format
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                
                # Проверяем валидность даты
                date_obj = datetime(year, month, day)
                return date_obj.strftime("%d.%m.%Y")
            except ValueError:
                continue
    
    return None

async def get_compatibility_analysis(date1, date2):
    """Получение анализа совместимости через Google Gemini API"""
    if not GEMINI_API_KEY:
        return "⚠️ API ключ Gemini не настроен. Пожалуйста, добавьте GEMINI_API_KEY в переменные окружения."
    
    try:
        prompt = f"""Ты астролог-эксперт. Проанализируй астрологическую совместимость двух человек:
        
Дата рождения 1: {date1}
Дата рождения 2: {date2}

Предоставь анализ в следующем формате:

🔮 АСТРОЛОГИЧЕСКИЙ АНАЛИЗ СОВМЕСТИМОСТИ

👤 Первый человек ({date1}):
• Знак зодиака: [знак]
• Стихия: [стихия]
• Основные черты: [краткое описание]

👤 Второй человек ({date2}):
• Знак зодиака: [знак]
• Стихия: [стихия]
• Основные черты: [краткое описание]

💕 СОВМЕСТИМОСТЬ В ЛЮБВИ: [процент]%
[2-3 предложения анализа]

🤝 СОВМЕСТИМОСТЬ В ДРУЖБЕ: [процент]%
[2-3 предложения анализа]

💼 СОВМЕСТИМОСТЬ В РАБОТЕ: [процент]%
[2-3 предложения анализа]

📊 ОБЩАЯ СОВМЕСТИМОСТЬ: [процент]%

✨ РЕКОМЕНДАЦИИ:
• [рекомендация 1]
• [рекомендация 2]
• [рекомендация 3]

Используй эмодзи для оформления."""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
                headers={
                    "Content-Type": "application/json"
                },
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 1024
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    content = data['candidates'][0]['content']
                    if 'parts' in content and len(content['parts']) > 0:
                        return content['parts'][0]['text']
                    else:
                        return "❌ Не удалось получить ответ от Gemini"
                else:
                    return "❌ Gemini не вернул результат"
            elif response.status_code == 429:
                return (
                    "⚠️ Превышен лимит запросов к Gemini API (ошибка 429)\n\n"
                    "Пожалуйста, подождите минуту и попробуйте снова."
                )
            elif response.status_code == 400:
                error_data = response.json()
                logger.error(f"Gemini API 400 error: {error_data}")
                return f"❌ Неверный запрос к Gemini API. Проверьте настройки."
            elif response.status_code == 403:
                return (
                    "❌ Доступ запрещен (ошибка 403)\n\n"
                    "Возможные причины:\n"
                    "• Неверный API ключ Gemini\n"
                    "• API ключ не активирован\n"
                    "• Gemini API недоступен в вашем регионе\n\n"
                    "Получите новый ключ на https://aistudio.google.com/apikey"
                )
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return f"❌ Ошибка Gemini API: {response.status_code}"
                
    except httpx.TimeoutException:
        return "⏱ Превышено время ожидания. Попробуйте еще раз."
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return f"❌ Произошла ошибка: {str(e)}"

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.first_name}! 👋\n\n'
        f'Я AstroHarmony бот - помогу узнать астрологическую совместимость! ✨\n\n'
        f'📋 Команды:\n'
        f'/start - начать\n'
        f'/help - помощь\n'
        f'/date - показать текущую дату\n'
        f'/compatibility - начать анализ совместимости\n\n'
        f'Или просто отправь мне две даты рождения для анализа! 🔮\n\n'
        f'Работает на Google Gemini AI 🌟'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📚 Как пользоваться ботом:\n\n'
        '1️⃣ Отправь команду /compatibility\n'
        '2️⃣ Введи первую дату рождения\n'
        '3️⃣ Введи вторую дату рождения\n'
        '4️⃣ Получи анализ совместимости! 🔮\n\n'
        '📅 Форматы дат:\n'
        '• 15.03.1990\n'
        '• 15/03/1990\n'
        '• 1990-03-15\n\n'
        'Или просто напиши две даты в одном сообщении:\n'
        '"15.03.1990 и 22.07.1985"\n\n'
        '🌟 Работает на Google Gemini AI'
    )

async def date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /date - показывает текущую дату и время"""
    now = datetime.now()
    
    # Форматируем дату и время по-русски
    date_str = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M:%S")
    weekday = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][now.weekday()]
    
    message = (
        f"📅 Текущая дата и время:\n\n"
        f"🗓 Дата: {date_str}\n"
        f"🕐 Время: {time_str}\n"
        f"📆 День недели: {weekday}"
    )
    
    await update.message.reply_text(message)

async def compatibility_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса анализа совместимости"""
    user_id = update.effective_user.id
    user_states[user_id] = {'step': 'waiting_first_date'}
    
    await update.message.reply_text(
        '🔮 Начинаем анализ совместимости!\n\n'
        '📅 Введите первую дату рождения\n'
        'Формат: ДД.ММ.ГГГГ (например, 15.03.1990)'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Проверяем, есть ли в сообщении сразу две даты
    dates = re.findall(r'\d{1,2}[./\-]\d{1,2}[./\-]\d{4}', text)
    
    if len(dates) >= 2:
        # Пользователь отправил сразу две даты
        date1 = parse_date(dates[0])
        date2 = parse_date(dates[1])
        
        if date1 and date2:
            await update.message.reply_text(
                f'✨ Анализирую совместимость через Google Gemini AI...\n\n'
                f'📅 Дата 1: {date1}\n'
                f'📅 Дата 2: {date2}\n\n'
                f'⏳ Пожалуйста, подождите...'
            )
            
            result = await get_compatibility_analysis(date1, date2)
            await update.message.reply_text(result)
            
            # Очищаем состояние
            if user_id in user_states:
                del user_states[user_id]
            return
    
    # Обработка пошагового ввода
    if user_id in user_states:
        state = user_states[user_id]
        
        if state['step'] == 'waiting_first_date':
            date1 = parse_date(text)
            if date1:
                user_states[user_id] = {'step': 'waiting_second_date', 'date1': date1}
                await update.message.reply_text(
                    f'✅ Первая дата: {date1}\n\n'
                    f'📅 Теперь введите вторую дату рождения'
                )
            else:
                await update.message.reply_text(
                    '❌ Неверный формат даты!\n'
                    'Используйте формат: ДД.ММ.ГГГГ (например, 15.03.1990)'
                )
        
        elif state['step'] == 'waiting_second_date':
            date2 = parse_date(text)
            if date2:
                date1 = state['date1']
                
                await update.message.reply_text(
                    f'✨ Анализирую совместимость через Google Gemini AI...\n\n'
                    f'📅 Дата 1: {date1}\n'
                    f'📅 Дата 2: {date2}\n\n'
                    f'⏳ Пожалуйста, подождите...'
                )
                
                result = await get_compatibility_analysis(date1, date2)
                await update.message.reply_text(result)
                
                # Очищаем состояние
                del user_states[user_id]
            else:
                await update.message.reply_text(
                    '❌ Неверный формат даты!\n'
                    'Используйте формат: ДД.ММ.ГГГГ (например, 15.03.1990)'
                )
    else:
        # Обычный echo
        await update.message.reply_text(
            f'Вы написали: {text}\n\n'
            f'Хотите узнать совместимость? Используйте команду /compatibility\n'
            f'Или отправьте сразу две даты в формате "15.03.1990 и 22.07.1985"'
        )

# Flask маршруты
@app.route('/')
def index():
    return 'Telegram Bot is running! ✅ Powered by Google Gemini AI 🌟', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработка входящих обновлений от Telegram"""
    try:
        app_instance = get_application()
        if app_instance is None:
            logger.error("Application not initialized")
            return 'Application not ready', 503
        
        # Используем бота из application, который уже инициализирован
        update = Update.de_json(request.get_json(force=True), app_instance.bot)
        
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
        
        # Получаем инициализированное приложение
        app_instance = get_application()
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Удаляем старый webhook
        loop.run_until_complete(app_instance.bot.delete_webhook(drop_pending_updates=True))
        
        # Устанавливаем новый
        result = loop.run_until_complete(app_instance.bot.set_webhook(url=webhook_url))
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
        app_instance = get_application()
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        info = loop.run_until_complete(app_instance.bot.get_webhook_info())
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
