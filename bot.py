import os
import telebot
import google.generativeai as genai

# --- TOKENS ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")


def gemini_answer(prompt):
    response = model.generate_content(prompt)
    return response.text


# --- START ---
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "✨ Добро пожаловать в AstroHarmony!\n\n"
        "🔮 Совместимость\n"
        "🔢 Нумерология\n"
        "🌌 Астрология\n"
        "🃏 Таро\n\n"
        "Выбери команду из меню 👇"
    )


# --- HELP ---
@bot.message_handler(commands=['help'])
def help_cmd(msg):
    bot.send_message(
        msg.chat.id,
        "📌 Команды:\n"
        "/compatibility — совместимость\n"
        "/numerology — нумерология\n"
        "/astrology — астрология\n"
        "/synastry — синастрия\n"
        "/life_path — путь жизни\n"
        "/tarot — мини таро\n"
        "/profile — астропрофиль\n\n"
        "💎 Полный разбор: /full"
    )


# --- COMPATIBILITY (заглушка, можно расширять) ---
@bot.message_handler(commands=['compatibility'])
def compatibility(msg):
    bot.send_message(
        msg.chat.id,
        "💞 Совместимость показывает общий потенциал пары.\n\n"
        "✨ Сейчас доступен краткий результат.\n"
        "🔓 Полный анализ: /full"
    )


# --- NUMEROLOGY ---
@bot.message_handler(commands=['numerology'])
def numerology(msg):
    prompt = (
        "Краткий нумерологический портрет личности. "
        "5–6 предложений, интригующе, без полного раскрытия."
    )
    text = gemini_answer(prompt)
    bot.send_message(msg.chat.id, text + "\n\n💎 Полный разбор: /full")


# --- ASTROLOGY ---
@bot.message_handler(commands=['astrology'])
def astrology(msg):
    prompt = (
        "Краткое астрологическое описание личности "
        "по знаку зодиака. Мистический стиль."
    )
    text = gemini_answer(prompt)
    bot.send_message(msg.chat.id, text + "\n\n🌌 Хочешь глубже? /full")


# --- SYNASTRY ---
@bot.message_handler(commands=['synastry'])
def synastry(msg):
    prompt = (
        "Краткий обзор синастрии двух людей: "
        "эмоции, притяжение, риск."
    )
    text = gemini_answer(prompt)
    bot.send_message(msg.chat.id, text + "\n\n💞 Полная синастрия: /full")


# --- LIFE PATH ---
@bot.message_handler(commands=['life_path'])
def life_path(msg):
    prompt = (
        "Краткое значение числа жизненного пути. "
        "Мотивирующе и интригующе."
    )
    text = gemini_answer(prompt)
    bot.send_message(msg.chat.id, text + "\n\n🔓 Полное значение: /full")


# --- TAROT ---
@bot.message_handler(commands=['tarot'])
def tarot(msg):
    prompt = (
        "Мини таро-расклад на сегодня: "
        "1 карта, общий посыл."
    )
    text = gemini_answer(prompt)
    bot.send_message(msg.chat.id, text + "\n\n🃏 Полный расклад: /full")


# --- PROFILE ---
@bot.message_handler(commands=['profile'])
def profile(msg):
    prompt = (
        "Краткий астрологический профиль личности: "
        "характер, сильная сторона, потенциал."
    )
    text = gemini_answer(prompt)
    bot.send_message(msg.chat.id, text + "\n\n✨ Полный профиль: /full")


# --- FULL (ПЛАТНО) ---
@bot.message_handler(commands=['full'])
def full(msg):
    bot.send_message(
        msg.chat.id,
        "💎 ПОЛНЫЙ ASTRO-ПАКЕТ\n\n"
        "✔ Нумерология\n"
        "✔ Астрология\n"
        "✔ Совместимость\n"
        "✔ Синастрия\n"
        "✔ Рекомендации\n\n"
        "🔒 Доступ по оплате\n"
        "Напиши «ХОЧУ ПОЛНЫЙ» ✨"
    )


bot.polling(none_stop=True)
