import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# === ВСТАВЬ СВОИ КЛЮЧИ СЮДА ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "ВАШ_ТОКЕН_ТЕЛЕГРАМ")
GROK_API_KEY = os.getenv("GROK_API_KEY", "ВАШ_КЛЮЧ_ГРОКА")

# === GROK CLIENT ===
client = OpenAI(
    api_key=GROK_API_KEY,
    base_url="https://api.x.ai/v1"
)

logging.basicConfig(level=logging.INFO)

# === SYSTEM PROMPT ===
SYSTEM_PROMPT = """Ты — нарративный движок интерактивной истории. Твоя задача вести мрачную, реалистичную историю без прикрас.

СЕТТИНГ:
Вечеринка в чужой квартире. 2024 год. Обычный город. Игрок — молодой человек, пришёл просто провести время.
Рядом оказывается девушка — тихая, в тёмной одежде, немного странная. Не агрессивная, просто... другая. Видно что за её молчанием есть что-то тяжёлое, но она не говорит об этом.

ТВОЯ РОЛЬ:
- Ты описываешь происходящее от третьего лица, коротко и атмосферно
- После каждой сцены даёшь игроку 2-3 варианта действий в виде пронумерованного списка
- Никаких мыслей персонажей в тексте — только действия, слова, детали
- История реалистичная. Если игрок пишет что-то абсурдное (достаёт оружие, нападает на копа, улетает на Марс) — мир реагирует реалистично и жёстко. Охрана выкидывает, копы скручивают, история идёт своим путём
- Никаких подсказок что правильно а что нет. Никакой морали вслух.
- Темп медленный. Последствия приходят не сразу.
- Девушка отвечает коротко, иногда странно, иногда с паузой. Читай между строк — или не читай.

ТОНАЛЬНОСТЬ:
Серая. Не злая, не добрая. Просто настоящая. Как жизнь.

ВАЖНО:
- Никогда не выходи из роли
- Никогда не объясняй механику игры
- Если игрок пишет не цифру а текст — интерпретируй как действие персонажа в рамках реального мира
- История имеет несколько концовок. Игрок не знает в какой ветке он находится.

НАЧАЛО:
Когда получаешь /start — начни историю с первой сцены на вечеринке."""

# === ХРАНИЛИЩЕ ДИАЛОГОВ ===
user_sessions = {}

def get_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = []
    return user_sessions[user_id]

def clear_session(user_id):
    user_sessions[user_id] = []

# === ЗАПРОС К GROK ===
async def ask_grok(user_id, user_message):
    history = get_session(user_id)
    history.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            max_tokens=600,
            temperature=0.85
        )
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        # Ограничиваем историю — последние 20 сообщений
        if len(history) > 20:
            user_sessions[user_id] = history[-20:]
        return reply
    except Exception as e:
        logging.error(f"Grok error: {e}")
        return "Что-то пошло не так. Попробуй ещё раз."

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_session(user_id)
    reply = await ask_grok(user_id, "/start")
    await update.message.reply_text(reply)

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_session(user_id)
    await update.message.reply_text("История начинается заново...\n")
    reply = await ask_grok(user_id, "/start")
    await update.message.reply_text(reply)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    reply = await ask_grok(user_id, text)
    await update.message.reply_text(reply)

# === MAIN ===
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
