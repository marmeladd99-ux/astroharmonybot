import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import asyncio
from queue import Queue

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен и URL из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

# Создаем Flask приложение
app = Flask(__name__)

# Создаем бота
bot = Bot(token=TOKEN)

# Создаем диспетчер
update_queue = Queue()
dispatcher = Dispatcher(bot, update_queue, use_context=True)

# Обработчик команды /start
def start(update, context):
    update.message.reply_text(
        '👋 Привет! Я AstroHarmony бот.\n\n'
        'Отправь мне свою дату рождения в формате ДД.ММ.ГГГГ (например, 15.03.1990), '
        'и я расскажу о твоем знаке зодиака!\n\n'
        'Или отправь две даты через " и " для проверки совместимости:\n'
        '15.03.1990 и 22.07.1985'
    )

# Обработчик команды /compatibility
def compatibility_command(update, context):
    update.message.reply_text(
        '💕 Для проверки совместимости отправьте две даты в формате:\n'
        '15.03.1990 и 22.07.1985\n\n'
        'Или просто отправьте две даты через " и "'
    )

def get_zodiac_sign(day, month):
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

def get_compatibility(sign1, sign2):
    """Определяет совместимость двух знаков (упрощенная версия)"""
    # Получаем только символ знака
    s1 = sign1.split()[0]
    s2 = sign2.split()[0]
    
    # Упрощенная матрица совместимости
    compatibility_map = {
        ('♈', '♌'): 95, ('♈', '♐'): 90, ('♈', '♊'): 85,
        ('♉', '♍'): 95, ('♉', '♑'): 90, ('♉', '♋'): 85,
        ('♊', '♎'): 95, ('♊', '♒'): 90, ('♊', '♈'): 85,
        ('♋', '♏'): 95, ('♋', '♓'): 90, ('♋', '♉'): 85,
        ('♌', '♈'): 95, ('♌', '♐'): 90, ('♌', '♊'): 85,
        ('♍', '♉'): 95, ('♍', '♑'): 90, ('♍', '♏'): 85,
        ('♎', '♊'): 95, ('♎', '♒'): 90, ('♎', '♐'): 85,
        ('♏', '♋'): 95, ('♏', '♓'): 90, ('♏', '♑'): 85,
        ('♐', '♈'): 90, ('♐', '♌'): 90, ('♐', '♎'): 85,
        ('♑', '♉'): 90, ('♑', '♍'): 90, ('♑', '♏'): 85,
        ('♒', '♊'): 90, ('♒', '♎'): 90, ('♒', '♐'): 85,
        ('♓', '♋'): 90, ('♓', '♏'): 90, ('♓', '♉'): 85,
    }
    
    # Проверяем оба варианта (знак1-знак2 и знак2-знак1)
    score = compatibility_map.get((s1, s2)) or compatibility_map.get((s2, s1)) or 70
    
    if score >= 90:
        level = "Отличная"
        emoji = "💚💚💚"
    elif score >= 80:
        level = "Хорошая"
        emoji = "💚💚"
    elif score >= 70:
        level = "Средняя"
        emoji = "💛"
    else:
        level = "Низкая"
        emoji = "🧡"
    
    return score, level, emoji

# Обработчик текстовых сообщений
def handle_message(update, context):
    user_message = update.message.text.strip()
    
    # Проверяем, есть ли " и " в сообщении (для совместимости)
    if ' и ' in user_message or ' И ' in user_message:
        # Разделяем две даты
        parts = user_message.replace(' И ', ' и ').split(' и ')
        if len(parts) == 2:
            try:
                # Парсим первую дату
                date1_parts = parts[0].strip().split('.')
                day1, month1, year1 = map(int, date1_parts)
                
                # Парсим вторую дату
                date2_parts = parts[1].strip().split('.')
                day2, month2, year2 = map(int, date2_parts)
                
                # Получаем знаки зодиака
                sign1 = get_zodiac_sign(day1, month1)
                sign2 = get_zodiac_sign(day2, month2)
                
                # Проверяем совместимость
                score, level, emoji = get_compatibility(sign1, sign2)
                
                response = f'📅 Дата 1: {parts[0].strip()}\n'
                response += f'🌟 Знак зодиака: {sign1}\n\n'
                response += f'📅 Дата 2: {parts[1].strip()}\n'
                response += f'🌟 Знак зодиака: {sign2}\n\n'
                response += f'💕 Совместимость: {level} {emoji}\n'
                response += f'📊 Оценка: {score}%\n\n'
                response += '⏳ Пожалуйста, подождите...\n'
                response += 'Готовлю для вас подробный анализ совместимости!'
                
                update.message.reply_text(response)
                return
                
            except (ValueError, IndexError):
                update.message.reply_text(
                    '❌ Неправильный формат дат.\n'
                    'Используйте формат: ДД.ММ.ГГГГ и ДД.ММ.ГГГГ\n'
                    'Например: 15.03.1990 и 22.07.1985'
                )
                return
    
    # Обработка одной даты
    if len(user_message.split('.')) == 3:
        try:
            day, month, year = map(int, user_message.split('.'))
            
            # Проверка валидности даты
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2024):
                raise ValueError
            
            zodiac_sign = get_zodiac_sign(day, month)
            
            response = f'📅 Ваша дата рождения: {user_message}\n'
            response += f'🌟 Ваш знак зодиака: {zodiac_sign}\n\n'
            response += '💡 Хотите узнать совместимость?\n'
            response += 'Используйте команду /compatibility\n'
            response += 'Или отправьте сразу две даты в формате:\n'
            response += '"15.03.1990 и 22.07.1985"'
            
            update.message.reply_text(response)
        except ValueError:
            update.message.reply_text(
                '❌ Неправильный формат даты.\n'
                'Пожалуйста, используйте формат ДД.ММ.ГГГГ\n'
                'Например: 15.03.1990'
            )
    else:
        update.message.reply_text(
            '❌ Неправильный формат.\n\n'
            '📝 Для одной даты: 15.03.1990\n'
            '💕 Для совместимости: 15.03.1990 и 22.07.1985\n'
            '📋 Или используйте команду /compatibility'
        )

# Регистрация обработчиков
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("compatibility", compatibility_command))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Webhook endpoint
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Обработка входящих обновлений через webhook"""
    json_data = request.get_json()
    update = Update.de_json(json_data, bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/')
def index():
    return 'AstroHarmony Bot is running! 🌟'

@app.route('/health')
def health():
    return 'OK'

@app.route('/set_webhook')
def set_webhook():
    """Установка webhook (вызовите этот URL один раз после деплоя)"""
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
        bot.set_webhook(url=webhook_url)
        return f'Webhook set to {webhook_url}'
    return 'WEBHOOK_URL not set'

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
