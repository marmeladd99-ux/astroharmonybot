import os
import logging
import re
from datetime import datetime
from quart import Quart, request
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

# Quart приложение
app = Quart(__name__)

# Получаем токен из переменных окружения
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
PORT = int(os.environ.get('PORT', 10000))

logger.info(f"Starting bot with PORT={PORT}, WEBHOOK_URL={WEBHOOK_URL}")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set!")

if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not set! Compatibility analysis will not work.")

# Создаем настройки для HTTP запросов
request_instance = HTTPXRequest(
    connection_pool_size=20,
    connect_timeout=30.0,
    read_timeout=30.0,
    write_timeout=30.0,
    pool_timeout=30.0
)

# Глобальная переменная для application
application = None

# Словарь для хранения состояния пользователей
user_states = {}

async def get_application():
    """Асинхронная инициализация application"""
    global application
    
    if application is None:
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
        
        # Инициализируем асинхронно
        await application.initialize()
        await application.start()
        logger.info("Application initialized and started")
    
    return application

def parse_date(text):
    """Парсинг даты из текста"""
    patterns = [
        r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})',
        r'(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if len(groups[0]) == 4:
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                else:
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                
                date_obj = datetime(year, month, day)
                return date_obj.strftime("%d.%m.%Y")
            except ValueError:
                continue
    
    return None

def get_zodiac_sign(day, month):
    """Определение знака зодиака"""
    zodiac_signs = [
        (1, 20, "Козерог"), (2, 19, "Водолей"), (3, 21, "Рыбы"),
        (4, 20, "Овен"), (5, 21, "Телец"), (6, 21, "Близнецы"),
        (7, 23, "Рак"), (8, 23, "Лев"), (9, 23, "Дева"),
        (10, 23, "Весы"), (11, 22, "Скорпион"), (12, 22, "Стрелец"),
        (12, 31, "Козерог")
    ]
    
    for end_month, end_day, sign in zodiac_signs:
        if month < end_month or (month == end_month and day <= end_day):
            return sign
    return "Козерог"

async def get_compatibility_analysis(date1, date2, name1="Он", name2="Она"):
    """Анализ совместимости через Groq API"""
    if not GROQ_API_KEY:
        return "⚠️ Сервис временно недоступен. Обратитесь к администратору."
    
    try:
        # Определяем знаки зодиака
        d1_parts = date1.split('.')
        d2_parts = date2.split('.')
        sign1 = get_zodiac_sign(int(d1_parts[0]), int(d1_parts[1]))
        sign2 = get_zodiac_sign(int(d2_parts[0]), int(d2_parts[1]))
        
        prompt = f"""Ты опытный психолог и астролог. Проанализируй совместимость пары.

Данные:
• {name1} ({sign1}) — {date1}
• {name2} ({sign2}) — {date2}

ФОРМАТ ОТВЕТА (строго соблюдай структуру с эмодзи):

🪄 Совместимость: {name1} ({sign1}) — {date1} и {name2} ({sign2}) — {date2}

📌 Кратко: [2-3 предложения о главном — притяжение, эмоции, ключевые особенности пары]

🧭 Психологически: [короткий анализ психологической динамики — кто открыт, кто закрыт, как проявляют чувства]

🔥 Химия: [1-2 предложения о романтической и сексуальной совместимости — высокая/средняя/низкая]

🏠 Быт и долгосрочность: [что поможет построить стабильные отношения и общий быт]

⚠️ Потенциальные проблемы: [1-2 главных риска и как их минимизировать]

✅ Совет: [один конкретный практический совет — что сделать прямо сейчас]

Пиши живо, по-человечески, без штампов. Будь конкретным и практичным."""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты опытный психолог и астролог. Отвечай структурированно, конкретно и с эмодзи."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.8,
                    "max_tokens": 1500
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
                return "❌ Не удалось получить ответ"
            elif response.status_code == 429:
                return "⚠️ Слишком много запросов. Попробуйте через минуту."
            elif response.status_code == 401:
                return "❌ Ошибка авторизации. Проверьте настройки."
            else:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                return f"❌ Ошибка сервиса: {response.status_code}"
                
    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        return f"❌ Произошла ошибка: {str(e)}"

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.first_name}! 👋\n\n'
        f'Я AstroHarmony бот — помогу узнать совместимость в отношениях! ✨\n\n'
        f'📋 Команды:\n'
        f'/start — начать\n'
        f'/help — помощь\n'
        f'/date — показать текущую дату\n'
        f'/compatibility — анализ совместимости\n\n'
        f'💡 Просто отправь две даты для быстрого анализа! 🔮'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📚 Как использовать:\n\n'
        '1️⃣ /compatibility\n'
        '2️⃣ Первая дата рождения\n'
        '3️⃣ Вторая дата рождения\n'
        '4️⃣ Получи анализ! 🔮\n\n'
        '📅 Форматы:\n'
        '• 15.03.1990\n'
        '• 15/03/1990\n'
        '• 1990-03-15\n\n'
        '💨 Быстро:\n'
        '"15.03.1990 и 22.07.1985"'
    )

async def date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущую дату"""
    now = datetime.now()
    date_str = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M:%S")
    weekday = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][now.weekday()]
    
    await update.message.reply_text(
        f"📅 Текущая дата и время:\n\n"
        f"🗓 Дата: {date_str}\n"
        f"🕐 Время: {time_str}\n"
        f"📆 День: {weekday}"
    )

async def compatibility_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало анализа"""
    user_id = update.effective_user.id
    user_states[user_id] = {'step': 'waiting_first_date'}
    
    await update.message.reply_text(
        '🔮 Анализ совместимости\n\n'
        '📅 Введите первую дату рождения\n'
        'Формат: ДД.ММ.ГГГГ (например, 15.03.1990)'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Поиск двух дат в сообщении
    dates = re.findall(r'\d{1,2}[./\-]\d{1,2}[./\-]\d{4}', text)
    
    if len(dates) >= 2:
        date1 = parse_date(dates[0])
        date2 = parse_date(dates[1])
        
        if date1 and date2:
            name1 = "Он"
            name2 = "Она"
            
            await update.message.reply_text(
                f'✨ Анализирую совместимость...\n\n'
                f'📅 {name1}: {date1}\n'
                f'📅 {name2}: {date2}\n\n'
                f'⏳ Один момент...'
            )
            
            result = await get_compatibility_analysis(date1, date2, name1, name2)
            await update.message.reply_text(result)
            
            if user_id in user_states:
                del user_states[user_id]
            return
    
    # Пошаговый ввод
    if user_id in user_states:
        state = user_states[user_id]
        
        if state['step'] == 'waiting_first_date':
            date1 = parse_date(text)
            if date1:
                user_states[user_id] = {'step': 'waiting_second_date', 'date1': date1}
                await update.message.reply_text(
                    f'✅ Первая дата: {date1}\n\n'
                    f'📅 Теперь вторую дату'
                )
            else:
                await update.message.reply_text('❌ Неверный формат! Пример: 15.03.1990')
        
        elif state['step'] == 'waiting_second_date':
            date2 = parse_date(text)
            if date2:
                date1 = state['date1']
                
                await update.message.reply_text(
                    f'✨ Анализирую...\n\n'
                    f'📅 Дата 1: {date1}\n'
                    f'📅 Дата 2: {date2}\n\n'
                    f'⏳ Момент...'
                )
                
                result = await get_compatibility_analysis(date1, date2)
                await update.message.reply_text(result)
                
                del user_states[user_id]
            else:
                await update.message.reply_text('❌ Неверный формат! Пример: 15.03.1990')
    else:
        await update.message.reply_text(
            f'Вы написали: {text}\n\n'
            f'💡 Используйте /compatibility или отправьте две даты:\n'
            f'"15.03.1990 и 22.07.1985"'
        )

# Quart маршруты
@app.route('/')
async def index():
    return 'AstroHarmony Bot ✅ 🔮', 200

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Обработка webhook"""
    try:
        app_instance = await get_application()
        json_data = await request.get_json()
        update = Update.de_json(json_data, app_instance.bot)
        await app_instance.process_update(update)
        return 'ok', 200
    except Exception as e:
        logger.error(f'Error: {e}', exc_info=True)
        return 'error', 500

@app.route('/set_webhook')
async def set_webhook():
    """Установка webhook"""
    try:
        if not WEBHOOK_URL:
            return 'WEBHOOK_URL not set', 500
        webhook_url = f"{WEBHOOK_URL}/webhook"
        app_instance = await get_application()
        await app_instance.bot.delete_webhook(drop_pending_updates=True)
        result = await app_instance.bot.set_webhook(url=webhook_url)
        logger.info(f'Webhook set to {webhook_url}')
        return f'Webhook set. Result: {result}', 200
    except Exception as e:
        logger.error(f'Error: {e}', exc_info=True)
        return f'Error: {str(e)}', 500

@app.route('/webhook_info')
async def webhook_info():
    """Инфо webhook"""
    try:
        app_instance = await get_application()
        info = await app_instance.bot.get_webhook_info()
        return {
            'url': info.url,
            'pending_update_count': info.pending_update_count,
            'last_error_date': str(info.last_error_date) if info.last_error_date else None,
            'last_error_message': info.last_error_message
        }, 200
    except Exception as e:
        logger.error(f'Error: {e}', exc_info=True)
        return f'Error: {str(e)}', 500

if __name__ == '__main__':
    logger.info(f"Starting on 0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
