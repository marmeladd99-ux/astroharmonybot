import os
import logging
from flask import Flask, request
from telegram import Bot, Update
import re
import asyncio
from functools import wraps

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

# Создаем единый event loop для всех асинхронных операций
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Создаем бота
bot = Bot(token=TOKEN)

def run_async(func):
    """Декоратор для запуска асинхронных функций"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper

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
    """Определяет совместимость двух знаков"""
    s1 = sign1.split()[0]
    s2 = sign2.split()[0]
    
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

@run_async
async def send_message(chat_id, text):
    """Отправка сообщения"""
    await bot.send_message(chat_id=chat_id, text=text)

def process_message(message_text, chat_id):
    """Обработка сообщения"""
    text = message_text.strip()
    
    # Проверяем команду /start
    if text.startswith('/start'):
        response = (
            '👋 Привет! Я AstroHarmony бот.\n\n'
            'Отправь мне свою дату рождения в формате ДД.ММ.ГГГГ (например, 15.03.1990), '
            'и я расскажу о твоем знаке зодиака!\n\n'
            'Или отправь две даты через " и " для проверки совместимости:\n'
            '15.03.1990 и 22.07.1985'
        )
        send_message(chat_id, response)
        return
    
    # Проверяем команду /compatibility
    if text.startswith('/compatibility'):
        response = (
            '💕 Для проверки совместимости отправьте две даты в формате:\n'
            '15.03.1990 и 22.07.1985\n\n'
            'Или просто отправьте две даты через " и "'
        )
        send_message(chat_id, response)
        return
    
    # Проверяем, есть ли " и " в сообщении (для совместимости)
    if ' и ' in text.lower():
        parts = re.split(r'\s+и\s+', text, flags=re.IGNORECASE)
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
                response += 'Спасибо за использование AstroHarmony! ✨'
                
                send_message(chat_id, response)
                return
                
            except (ValueError, IndexError):
                response = (
                    '❌ Неправильный формат дат.\n'
                    'Используйте формат: ДД.ММ.ГГГГ и ДД.ММ.ГГГГ\n'
                    'Например: 15.03.1990 и 22.07.1985'
                )
                send_message(chat_id, response)
                return
    
    # Обработка одной даты
    if len(text.split('.')) == 3:
        try:
            day, month, year = map(int, text.split('.'))
            
            # Проверка валидности даты
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2025):
                raise ValueError
            
            zodiac_sign = get_zodiac_sign(day, month)
            
            response = f'📅 Ваша дата рождения: {text}\n'
            response += f'🌟 Ваш знак зодиака: {zodiac_sign}\n\n'
            response += '💡 Хотите узнать совместимость?\n'
            response += 'Используйте команду /compatibility\n'
            response += 'Или отправьте сразу две даты в формате:\n'
            response += '"15.03.1990 и 22.07.1985"'
            
            send_message(chat_id, response)
        except ValueError:
            response = (
                '❌ Неправильный формат даты.\n'
                'Пожалуйста, используйте формат ДД.ММ.ГГГГ\n'
                'Например: 15.03.1990'
            )
            send_message(chat_id, response)
    else:
        response = (
            '❌ Неправильный формат.\n\n'
            '📝 Для одной даты: 15.03.1990\n'
            '💕 Для совместимости: 15.03.1990 и 22.07.1985\n'
            '📋 Или используйте команду /compatibility'
        )
        send_message(chat_id, response)

# Webhook endpoint
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Обработка входящих обновлений через webhook"""
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, bot)
        
        if update.message and update.message.text:
            chat_id = update.message.chat_id
            message_text = update.message.text
            logger.info(f"Received message: {message_text} from chat_id: {chat_id}")
            process_message(message_text, chat_id)
        
        return 'ok'
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return 'ok'  # Возвращаем ok чтобы Telegram не повторял запрос

@app.route('/')
def index():
    return 'AstroHarmony Bot is running! 🌟'

@app.route('/health')
def health():
    return 'OK'

@app.route('/set_webhook')
def set_webhook():
    """Установка webhook"""
    try:
        if WEBHOOK_URL:
            webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
            
            @run_async
            async def set_wh():
                await bot.set_webhook(url=webhook_url)
            
            set_wh()
            logger.info(f"Webhook set to {webhook_url}")
            return f'Webhook set successfully to {webhook_url}'
        return 'WEBHOOK_URL not set'
    except Exception as e:
        logger.error(f'Error setting webhook: {e}')
        return f'Error setting webhook: {e}'

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
