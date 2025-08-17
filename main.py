import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
import threading
import time
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask приложение для пинга
app = Flask(__name__)

@app.route('/')
def home():
    return "FunPay Steam Bot is running!"

@app.route('/ping')
def ping():
    return "pong"

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
PORT = int(os.getenv('PORT', 8000))

# Глобальные переменные
funpay_token = None
active_rentals = {}
accounts_data = []

# Загрузка данных аккаунтов
def load_accounts():
    global accounts_data
    try:
        with open('accounts.json', 'r', encoding='utf-8') as f:
            accounts_data = json.load(f)
        logger.info(f"Загружено {len(accounts_data)} аккаунтов")
    except FileNotFoundError:
        logger.warning("Файл accounts.json не найден")
        accounts_data = []

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этому боту")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🎮 Аккаунты", callback_data="accounts")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *FunPay Steam Bot*\n\n"
        "Бот для автоматической аренды Steam аккаунтов\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def set_funpay_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа к этому боту")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /set_funpay_token <токен>")
        return
    
    global funpay_token
    funpay_token = context.args[0]
    await update.message.reply_text("✅ FunPay токен установлен!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        stats_text = f"""
📊 *Статистика бота*

🎮 Всего аккаунтов: {len(accounts_data)}
🔄 Активных аренд: {len(active_rentals)}
🟢 FunPay токен: {'✅ Установлен' if funpay_token else '❌ Не установлен'}
        """
        await query.edit_message_text(stats_text, parse_mode='Markdown')
    
    elif query.data == "accounts":
        if not accounts_data:
            await query.edit_message_text("❌ Аккаунты не загружены")
            return
        
        accounts_text = "🎮 *Список аккаунтов:*\n\n"
        for i, acc in enumerate(accounts_data[:5]):  # Показываем первые 5
            status = "🔄 Арендован" if acc.get('login') in active_rentals else "🟢 Свободен"
            accounts_text += f"{i+1}. {acc.get('login', 'N/A')} - {status}\n"
        
        if len(accounts_data) > 5:
            accounts_text += f"\n... и еще {len(accounts_data) - 5} аккаунтов"
        
        await query.edit_message_text(accounts_text, parse_mode='Markdown')
    
    elif query.data == "settings":
        settings_text = f"""
⚙️ *Настройки бота*

🔑 FunPay токен: {'✅ Установлен' if funpay_token else '❌ Не установлен'}
👤 Админ ID: {ADMIN_ID}
🌐 Порт: {PORT}

Для установки токена используйте:
/set_funpay_token <токен>
        """
        await query.edit_message_text(settings_text, parse_mode='Markdown')

# Функция мониторинга FunPay
def monitor_funpay():
    while True:
        try:
            if funpay_token:
                # Здесь будет логика мониторинга FunPay
                logger.info("Мониторинг FunPay активен")
            time.sleep(30)  # Проверка каждые 30 секунд
        except Exception as e:
            logger.error(f"Ошибка мониторинга FunPay: {e}")
            time.sleep(60)

# Запуск Flask сервера
def run_flask():
    app.run(host='0.0.0.0', port=PORT)

async def main():
    # Загружаем аккаунты
    load_accounts()
    
    # Создаем приложение Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set_funpay_token", set_funpay_token))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем мониторинг FunPay в отдельном потоке
    monitor_thread = threading.Thread(target=monitor_funpay, daemon=True)
    monitor_thread.start()
    
    logger.info("Бот запущен!")
    
    # Запускаем бота
    await application.run_polling()

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN не установлен!")
        exit(1)
    
    if ADMIN_ID == 0:
        logger.error("ADMIN_ID не установлен!")
        exit(1)
    
    asyncio.run(main())
