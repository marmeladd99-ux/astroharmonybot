import os
import logging
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
import re
import asyncio
from functools import wraps
import google.generativeai as genai
from datetime import datetime
import random

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токены из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found, using fallback responses")

# Настраиваем Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False
    logger.warning("Gemini not configured properly")

# Создаем Flask приложение
app = Flask(__name__)

# Создаем единый event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Создаем бота
bot = Bot(token=TOKEN)

# Хранилище данных пользователей
user_data = {}

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

def get_life_path_number(day, month, year):
    """Вычисляет число жизненного пути"""
    total = sum(int(d) for d in str(day) + str(month) + str(year))
    while total > 9 and total not in [11, 22, 33]:
        total = sum(int(d) for d in str(total))
    return total

def generate_with_gemini(prompt, max_length=400):
    """Генерирует текст через Gemini с резервными вариантами"""
    if not GEMINI_AVAILABLE:
        return None
    
    try:
        # Добавляем инструкции к промпту
        full_prompt = f"""{prompt}

Важно:
- Ответ должен быть кратким (2-3 предложения, максимум {max_length} символов)
- Используй эмодзи для украшения
- Будь позитивным и вдохновляющим
- Пиши на русском языке
- Не используй заголовки и форматирование markdown"""

        response = model.generate_content(full_prompt)
        
        if response and response.text:
            text = response.text.strip()
            
            # Ограничиваем длину
            if len(text) > max_length:
                # Обрезаем по последнему предложению
                sentences = text.split('.')
                result = ""
                for sentence in sentences:
                    if len(result + sentence + '.') <= max_length:
                        result += sentence + '.'
                    else:
                        break
                text = result if result else text[:max_length]
            
            return text
        
        return None
        
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return None

@run_async
async def send_message(chat_id, text, reply_markup=None):
    """Отправка сообщения"""
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=None)

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

def get_compatibility_fallback(sign1, sign2):
    """Резервный текст для совместимости"""
    templates = [
        f"Ваши знаки {sign1} и {sign2} создают гармоничный союз! 💫 Вы дополняете друг друга и понимаете с полуслова.",
        f"Союз {sign1} и {sign2} обещает быть ярким! ✨ У вас много общего, хотя иногда возможны небольшие разногласия.",
        f"Пара {sign1} и {sign2} - это интересное сочетание! 🌟 Вы можете многому научиться друг у друга."
    ]
    return random.choice(templates)

def handle_start(chat_id):
    """Обработка команды /start"""
    keyboard = [
        [InlineKeyboardButton("🔮 Astrology insights", callback_data='astrology')],
        [InlineKeyboardButton("💕 Relationship compatibility", callback_data='compatibility')],
        [InlineKeyboardButton("🔢 Personal numerology report", callback_data='numerology')],
        [InlineKeyboardButton("✨ Premium версия", callback_data='premium')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    response = (
        '🌟 Добро пожаловать в AstroHarmony!\n\n'
        'Я помогу вам узнать:\n'
        '• Совместимость в отношениях 💕\n'
        '• Астрологические прогнозы 🔮\n'
        '• Нумерологический анализ 🔢\n'
        '• Анализ синастрии ⭐\n'
        '• И многое другое!\n\n'
        'Выберите интересующую функцию:'
    )
    send_message(chat_id, response, reply_markup)

def handle_help(chat_id):
    """Обработка команды /help"""
    response = (
        '📚 Доступные команды:\n\n'
        '/start - Главное меню\n'
        '/compatibility - Совместимость пар\n'
        '/numerology - Нумерология\n'
        '/astrology - Астрологический анализ\n'
        '/synastry - Синастрия двух людей\n'
        '/life_path - Число жизненного пути\n'
        '/tarot - Мини расклад Таро\n'
        '/profile - Ваш астропрофиль\n'
        '/feedback - Оставить отзыв\n'
        '/premium - Premium версия\n\n'
        '💎 В Premium больше деталей и точности!'
    )
    send_message(chat_id, response)

def handle_compatibility_request(chat_id):
    """Запрос данных для совместимости"""
    user_data[chat_id] = {'waiting_for': 'compatibility'}
    response = (
        '💕 Анализ совместимости\n\n'
        'Отправьте две даты рождения в формате:\n'
        '10.10.2010 и 30.07.2007'
    )
    send_message(chat_id, response)

def handle_compatibility(chat_id, date1, date2):
    """Обработка совместимости"""
    try:
        parts1 = date1.strip().split('.')
        day1, month1, year1 = map(int, parts1)
        
        parts2 = date2.strip().split('.')
        day2, month2, year2 = map(int, parts2)
        
        sign1 = get_zodiac_sign(day1, month1)
        sign2 = get_zodiac_sign(day2, month2)
        
        score, level, emoji = get_compatibility(sign1, sign2)
        
        # Пробуем Gemini
        prompt = f"""Напиши краткий анализ совместимости для пары (2-3 предложения):
Человек 1: {sign1}
Человек 2: {sign2}

Опиши их сильные стороны в отношениях."""
        
        ai_analysis = generate_with_gemini(prompt, max_length=300)
        
        # Если Gemini не сработал, используем резервный вариант
        if not ai_analysis:
            ai_analysis = get_compatibility_fallback(sign1, sign2)
        
        response = f'📅 Дата 1: {date1}\n'
        response += f'🌟 Знак: {sign1}\n\n'
        response += f'📅 Дата 2: {date2}\n'
        response += f'🌟 Знак: {sign2}\n\n'
        response += f'💕 Совместимость: {level} {emoji}\n'
        response += f'📊 Оценка: {score}%\n\n'
        response += f'🔮 Анализ:\n{ai_analysis}\n\n'
        response += '✨ Хотите детальный анализ? /premium'
        
        send_message(chat_id, response)
        
    except Exception as e:
        logger.error(f"Error in compatibility: {e}")
        send_message(chat_id, "❌ Ошибка. Формат: ДД.ММ.ГГГГ и ДД.ММ.ГГГГ")

def handle_numerology(chat_id):
    """Запрос даты для нумерологии"""
    user_data[chat_id] = {'waiting_for': 'numerology'}
    response = (
        '🔢 Нумерологический отчет\n\n'
        'Отправьте дату рождения:\n'
        'ДД.ММ.ГГГГ (например: 15.03.1990)'
    )
    send_message(chat_id, response)

def handle_numerology_analysis(chat_id, date):
    """Нумерологический анализ"""
    try:
        day, month, year = map(int, date.split('.'))
        
        life_path = get_life_path_number(day, month, year)
        zodiac = get_zodiac_sign(day, month)
        
        prompt = f"""Напиши краткое описание числа жизненного пути {life_path} (2-3 предложения):
Расскажи о главных чертах характера и талантах."""
        
        ai_analysis = generate_with_gemini(prompt, max_length=300)
        
        if not ai_analysis:
            meanings = {
                1: "Вы прирожденный лидер! 👑 Независимость и инициативность - ваши сильные стороны. Вы умеете вдохновлять других.",
                2: "Вы миротворец и дипломат! 🕊️ Чуткость и способность к сотрудничеству помогают вам в отношениях.",
                3: "Вы творческая личность! 🎨 Общительность и оптимизм делают вас душой компании.",
                4: "Вы надежный и практичный! 🏗️ Дисциплина и трудолюбие - залог вашего успеха.",
                5: "Вы свободолюбивы и любознательны! ✈️ Жажда приключений ведет вас по жизни.",
                6: "Вы заботливы и ответственны! 💝 Гармония в семье для вас на первом месте.",
                7: "Вы мудры и аналитичны! 🧘 Духовный поиск и самопознание - ваш путь.",
                8: "Вы амбициозны и целеустремленны! 💰 Материальный успех вам по плечу.",
                9: "Вы гуманист и идеалист! 🌍 Помощь людям приносит вам радость.",
                11: "У вас мастер-число! ⚡ Интуиция и вдохновение - ваши дары.",
                22: "У вас мастер-число! 🌟 Вы можете воплотить грандиозные идеи.",
                33: "У вас мастер-число! 💫 Вы несете свет и любовь в мир."
            }
            ai_analysis = meanings.get(life_path, "У вас особенное число! Вы уникальны и талантливы.")
        
        response = f'🔢 Нумерологический анализ\n\n'
        response += f'📅 Дата: {date}\n'
        response += f'🌟 Знак: {zodiac}\n'
        response += f'🔮 Число жизненного пути: {life_path}\n\n'
        response += f'{ai_analysis}\n\n'
        response += '✨ Полный отчет в Premium: /premium'
        
        send_message(chat_id, response)
        
    except Exception as e:
        logger.error(f"Error in numerology: {e}")
        send_message(chat_id, "❌ Неверный формат. Используйте: ДД.ММ.ГГГГ")

def handle_astrology(chat_id):
    """Запрос даты для астрологии"""
    user_data[chat_id] = {'waiting_for': 'astrology'}
    response = (
        '🔮 Астрологический анализ\n\n'
        'Отправьте дату рождения:\n'
        'ДД.ММ.ГГГГ'
    )
    send_message(chat_id, response)

def handle_astrology_analysis(chat_id, date):
    """Астрологический анализ"""
    try:
        day, month, year = map(int, date.split('.'))
        zodiac = get_zodiac_sign(day, month)
        
        prompt = f"""Напиши краткий прогноз для знака {zodiac} на текущий период (2-3 предложения):
Дай позитивные рекомендации."""
        
        ai_analysis = generate_with_gemini(prompt, max_length=300)
        
        if not ai_analysis:
            forecasts = {
                "♈ Овен": "Сейчас отличное время для новых начинаний! 🚀 Ваша энергия на пике, используйте её для достижения целей.",
                "♉ Телец": "Период стабильности и роста! 🌱 Сосредоточьтесь на финансах и близких отношениях.",
                "♊ Близнецы": "Время общения и новых знакомств! 💬 Ваши идеи найдут отклик у окружающих.",
                "♋ Рак": "Обратите внимание на дом и семью! 🏡 Эмоциональная гармония важна сейчас.",
                "♌ Лев": "Ваше время сиять! ✨ Творческие проекты принесут успех и признание.",
                "♍ Дева": "Идеальный период для планирования! 📋 Организованность приведет к результатам.",
                "♎ Весы": "Гармония в отношениях на первом плане! ⚖️ Компромиссы принесут пользу.",
                "♏ Скорпион": "Время трансформации и глубины! 🔮 Доверяйте своей интуиции.",
                "♐ Стрелец": "Расширяйте горизонты! 🎯 Новые возможности ждут вас впереди.",
                "♑ Козерог": "Упорный труд вознаградится! ⛰️ Ваши усилия не останутся незамеченными.",
                "♒ Водолей": "Инновации и оригинальность! 💡 Ваши идеи опережают время.",
                "♓ Рыбы": "Духовность и творчество! 🎨 Слушайте свое сердце и мечтайте."
            }
            ai_analysis = forecasts.get(zodiac, "Прекрасный период для саморазвития! 🌟 Звезды благоволят вам.")
        
        response = f'🔮 Астрологический анализ\n\n'
        response += f'📅 Дата: {date}\n'
        response += f'🌟 Знак: {zodiac}\n\n'
        response += f'{ai_analysis}\n\n'
        response += '✨ Детальный прогноз на месяц: /premium'
        
        send_message(chat_id, response)
        
    except Exception as e:
        send_message(chat_id, "❌ Неверный формат даты")

def handle_synastry(chat_id):
    """Запрос для синастрии"""
    user_data[chat_id] = {'waiting_for': 'synastry'}
    response = (
        '⭐ Синастрия - анализ двух людей\n\n'
        'Отправьте две даты:\n'
        '10.10.2010 и 30.07.2007'
    )
    send_message(chat_id, response)

def handle_synastry_analysis(chat_id, date1, date2):
    """Анализ синастрии"""
    try:
        parts1 = date1.strip().split('.')
        day1, month1, year1 = map(int, parts1)
        
        parts2 = date2.strip().split('.')
        day2, month2, year2 = map(int, parts2)
        
        sign1 = get_zodiac_sign(day1, month1)
        sign2 = get_zodiac_sign(day2, month2)
        
        prompt = f"""Напиши краткую синастрию для пары (2-3 предложения):
Человек 1: {sign1}
Человек 2: {sign2}

Опиши динамику их отношений."""
        
        ai_analysis = generate_with_gemini(prompt, max_length=300)
        
        if not ai_analysis:
            ai_analysis = f"Ваши энергии {sign1} и {sign2} создают уникальную динамику! 💫 В отношениях есть как гармония, так и точки роста. Вместе вы можете достичь многого!"
        
        response = f'⭐ Синастрия\n\n'
        response += f'👤 Человек 1: {sign1}\n'
        response += f'👤 Человек 2: {sign2}\n\n'
        response += f'{ai_analysis}\n\n'
        response += '✨ Полная синастрия с домами: /premium'
        
        send_message(chat_id, response)
        
    except Exception as e:
        send_message(chat_id, "❌ Ошибка. Формат: ДД.ММ.ГГГГ и ДД.ММ.ГГГГ")

def handle_life_path(chat_id):
    """Запрос для числа пути"""
    user_data[chat_id] = {'waiting_for': 'life_path'}
    response = (
        '🛤️ Число жизненного пути\n\n'
        'Отправьте дату рождения:\n'
        'ДД.ММ.ГГГГ'
    )
    send_message(chat_id, response)

def handle_life_path_analysis(chat_id, date):
    """Анализ числа жизненного пути"""
    try:
        day, month, year = map(int, date.split('.'))
        life_path = get_life_path_number(day, month, year)
        
        prompt = f"""Напиши о значении числа жизненного пути {life_path} (2-3 предложения):
Расскажи о предназначении и миссии."""
        
        ai_analysis = generate_with_gemini(prompt, max_length=300)
        
        if not ai_analysis:
            missions = {
                1: "Ваша миссия - быть первопроходцем! 🎯 Вы создаете новые пути и вдохновляете других своей смелостью.",
                2: "Ваша миссия - объединять людей! 🤝 Гармония и партнерство - ваш дар миру.",
                3: "Ваша миссия - нести радость! 🎭 Творчество и самовыражение - ваш путь.",
                4: "Ваша миссия - создавать основу! 🏛️ Надежность и стабильность - ваш вклад.",
                5: "Ваша миссия - исследовать мир! 🗺️ Свобода и перемены - ваша стихия.",
                6: "Ваша миссия - заботиться! 💖 Любовь и служение - ваше призвание.",
                7: "Ваша миссия - искать истину! 📚 Мудрость и духовность - ваш путь.",
                8: "Ваша миссия - достигать успеха! 🏆 Сила и изобилие - ваши инструменты.",
                9: "Ваша миссия - помогать человечеству! 🌏 Сострадание и щедрость - ваш дар."
            }
            ai_analysis = missions.get(life_path, "Ваша миссия уникальна! ✨ Вы несете особый свет в этот мир.")
        
        response = f'🛤️ Число жизненного пути\n\n'
        response += f'📅 Дата: {date}\n'
        response += f'🔢 Ваше число: {life_path}\n\n'
        response += f'{ai_analysis}\n\n'
        response += '✨ Детальный разбор всех чисел: /premium'
        
        send_message(chat_id, response)
        
    except Exception as e:
        send_message(chat_id, "❌ Неверный формат даты")

def handle_tarot(chat_id):
    """Мини расклад Таро"""
    cards = [
        ("Маг", "Новые возможности и начинания! ✨ Используйте свои таланты для достижения целей."),
        ("Жрица", "Доверьтесь интуиции! 🌙 Ответы придут изнутри, слушайте свой внутренний голос."),
        ("Императрица", "Время творчества и изобилия! 👑 Природа и красота окружают вас."),
        ("Император", "Структура и контроль! ⚔️ Ваша дисциплина приведет к успеху."),
        ("Иерофант", "Следуйте традициям! 📖 Мудрость предков поможет найти путь."),
        ("Влюбленные", "Важный выбор! 💕 Прислушайтесь к сердцу в принятии решений."),
        ("Колесница", "Двигайтесь вперед! 🏇 Ваша целеустремленность преодолеет препятствия."),
        ("Сила", "Внутренняя мощь! 🦁 Мягкость и терпение сильнее грубой силы."),
        ("Отшельник", "Время для размышлений! 🕯️ Уединение принесет ясность."),
        ("Колесо Фортуны", "Перемены близко! 🎡 Доверьтесь течению жизни."),
        ("Справедливость", "Баланс восстановится! ⚖️ Правда выйдет наружу."),
        ("Повешенный", "Смените угол зрения! 🔄 Иногда нужно отпустить контроль."),
        ("Смерть", "Трансформация! 🦋 Старое уходит, давая место новому."),
        ("Умеренность", "Гармония и баланс! 🌈 Терпение приведет к результату."),
        ("Дьявол", "Освободитесь от оков! ⛓️ Осознайте свои зависимости."),
        ("Башня", "Разрушение иллюзий! ⚡ Это очищение для нового начала."),
        ("Звезда", "Надежда и вдохновение! ⭐ Мечты начнут сбываться."),
        ("Луна", "Интуиция и тайны! 🌙 Не все так, как кажется."),
        ("Солнце", "Радость и успех! ☀️ Все складывается наилучшим образом."),
        ("Суд", "Пробуждение! 📯 Время подвести итоги и начать заново."),
        ("Мир", "Завершение цикла! 🌍 Гармония и целостность достигнуты.")
    ]
    
    card_name, card_meaning = random.choice(cards)
    
    response = f'🔮 Карта дня: {card_name}\n\n'
    response += f'{card_meaning}\n\n'
    response += '✨ Полные расклады на 3/7 карт: /premium'
    
    send_message(chat_id, response)

def handle_profile(chat_id):
    """Астропрофиль пользователя"""
    user_data[chat_id] = {'waiting_for': 'profile'}
    response = (
        '👤 Ваш астропрофиль\n\n'
        'Отправьте дату рождения:\n'
        'ДД.ММ.ГГГГ'
    )
    send_message(chat_id, response)

def handle_profile_analysis(chat_id, date):
    """Создание профиля"""
    try:
        day, month, year = map(int, date.split('.'))
        zodiac = get_zodiac_sign(day, month)
        life_path = get_life_path_number(day, month, year)
        
        prompt = f"""Напиши краткую характеристику личности (2-3 предложения):
Знак: {zodiac}
Число пути: {life_path}

Опиши характер и особенности."""
        
        ai_analysis = generate_with_gemini(prompt, max_length=300)
        
        if not ai_analysis:
            ai_analysis = f"Вы {zodiac} с числом пути {life_path} - уникальное сочетание! 🌟 Ваша личность сочетает в себе качества знака и мудрость числа. Это делает вас особенным!"
        
        response = f'👤 Ваш профиль\n\n'
        response += f'🌟 Знак: {zodiac}\n'
        response += f'🔢 Число: {life_path}\n'
        response += f'📅 Дата: {date}\n\n'
        response += f'{ai_analysis}\n\n'
        response += '✨ Полный профиль с Луной и Асцендентом: /premium'
        
        send_message(chat_id, response)
        
    except Exception as e:
        send_message(chat_id, "❌ Неверный формат даты")

def handle_premium(chat_id):
    """Информация о Premium"""
    response = (
        '💎 AstroHarmony Premium\n\n'
        '✨ Что включено:\n\n'
        '📊 Полные детальные отчеты (в 3-5 раз больше информации)\n'
        '🔮 Персональные прогнозы на месяц/год\n'
        '💕 Детальная синастрия с домами и аспектами\n'
        '🎴 Расклады Таро на 3/7/10 карт\n'
        '📈 Транзиты и прогрессии\n'
        '🌙 Анализ Луны, Асцендента и всех планет\n'
        '⚡ Приоритетная поддержка\n'
        '🚀 Без ограничений по запросам\n\n'
        '💰 Цена: 990₽/месяц\n\n'
        '📞 Для покупки напишите:\n'
        '@astroharmony_support\n\n'
        'Или отправьте /feedback'
    )
    send_message(chat_id, response)

def handle_feedback(chat_id):
    """Обратная связь"""
    response = (
        '💬 Обратная связь\n\n'
        'Свяжитесь с нами для:\n'
        '• Покупки Premium\n'
        '• Вопросов и предложений\n'
        '• Технической поддержки\n\n'
        '📧 Email: support@astroharmony.com\n'
        '💬 Telegram: @astroharmony_support\n\n'
        'Мы ответим в течение 24 часов! 💫'
    )
    send_message(chat_id, response)

def process_message(message_text, chat_id):
    """Основная обработка сообщений"""
    text = message_text.strip()
    
    # Команды
    if text == '/start':
        handle_start(chat_id)
        return
    elif text == '/help':
        handle_help(chat_id)
        return
    elif text == '/compatibility':
        handle_compatibility_request(chat_id)
        return
    elif text == '/numerology':
        handle_numerology(chat_id)
        return
    elif text == '/astrology':
        handle_astrology(chat_id)
        return
    elif text == '/synastry':
        handle_synastry(chat_id)
        return
    elif text == '/life_path':
        handle_life_path(chat_id)
        return
    elif text == '/tarot':
        handle_tarot(chat_id)
        return
    elif text == '/profile':
        handle_profile(chat_id)
        return
    elif text == '/premium':
        handle_premium(chat_id)
        return
    elif text == '/feedback':
        handle_feedback(chat_id)
        return
    
    # Обработка ответов пользователя
    if chat_id in user_data:
        waiting_for = user_data[chat_id].get('waiting_for')
        
        if waiting_for == 'compatibility' and ' и ' in text.lower():
            parts = re.split(r'\s+и\s+', text, flags=re.IGNORECASE)
            if len(parts) == 2:
                handle_compatibility(chat_id, parts[0], parts[1])
                del user_data[chat_id]
                return
        
        elif waiting_for == 'numerology' and len(text.split('.')) == 3:
            handle_numerology_analysis(chat_id, text)
            del user_data[chat_id]
            return
        
        elif waiting_for == 'astrology' and len(text.split('.')) == 3:
            handle_astrology_analysis(chat_id, text)
            del user_data[chat_id]
            return
        
        elif waiting_for == 'synastry' and ' и ' in text.lower():
            parts = re.split(r'\s+и\s+', text, flags=re.IGNORECASE)
            if len(parts) == 2:
                handle_synastry_analysis(chat_id, parts[0], parts[1])
                del user_data[chat_id]
                return
        
        elif waiting_for == 'life_path' and len(text.split('.')) == 3:
            handle_life_path_analysis(chat_id, text)
            del user_data[chat_id]
            return
        
        elif waiting_for == 'profile' and len(text.split('.')) == 3:
            handle_profile_analysis(chat_id, text)
            del user_data[chat_id]
            return
    
    # Если не подошло ни под что
    response = (
        '❓ Не понял команду.\n\n'
        'Используйте /help для списка команд\n'
        'или /start для главного меню'
    )
    send_message(chat_id, response)

# Webhook endpoint
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Обработка входящих обновлений"""
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, bot)
        
        if update.message and update.message.text:
            chat_id = update.message.chat_id
            message_text = update.message.text
            logger.info(f"Received: {message_text} from {chat_id}")
            process_message(message_text, chat_id)
        
        # Обработка callback кнопок
        elif update.callback_query:
            query = update.callback_query
            chat_id = query.message.chat_id
            data = query.data
            
            if data == 'compatibility':
                handle_compatibility_request(chat_id)
            elif data == 'numerology':
                handle_numerology(chat_id)
            elif data == 'astrology':
                handle_astrology(chat_id)
            elif data == 'premium':
                handle_premium(chat_id)
        
        return 'ok'
    except Exception as e:
        logger.error(f"Error: {e}")
        return 'ok'

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
            return f'Webhook set to {webhook_url}'
        return 'WEBHOOK_URL not set'
    except Exception as e:
        logger.error(f'Error setting webhook: {e}')
        return f'Error: {e}'

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
