import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, PreCheckoutQueryHandler
import json
import os
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8749846490:AAH3DLfTRLKf9Wc6g0vKANboTV1CJcBArD4"
ADMIN_IDS = []  # Добавьте свой Telegram ID
MANAGER_USERNAME = "buyer_supportz"

# Курс и лимиты
STARS_TO_RUB = 1.6
MIN_STARS = 1  # Минимальная сумма для теста

# База данных
DATA_FILE = "data.json"
PHOTO_FILE = "bot_photo.jpg"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": {}, "transactions": []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def send_with_photo(chat_id, text, reply_markup=None, context=None, photo_file=PHOTO_FILE):
    """Отправляет новое сообщение с фото"""
    try:
        if os.path.exists(photo_file):
            with open(photo_file, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=InputFile(photo, filename=photo_file),
                    caption=text,
                    reply_markup=reply_markup
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке с фото: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )

async def edit_message(query, text, reply_markup=None):
    """Редактирует существующее сообщение"""
    try:
        if query.message.text:
            await query.edit_message_text(text, reply_markup=reply_markup)
        elif query.message.caption:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup)
        else:
            await query.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при редактировании: {e}")
        await query.message.reply_text(text, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.clear()
    context.user_data['state'] = 'main'
    
    data = load_data()
    if str(user.id) not in data["users"]:
        data["users"][str(user.id)] = {
            "username": user.username,
            "first_name": user.first_name,
            "joined_date": datetime.now().isoformat()
        }
        save_data(data)
    
    welcome_text = (
        f"🌟 Добро пожаловать в Скупку Звёзд Telegram, {user.first_name}!\n\n"
        "Мы профессионально покупаем Telegram Stars по самому выгодному курсу!\n\n"
        f"💰 Курс обмена: 1 звезда = {STARS_TO_RUB} ₽\n"
        f"📊 Минимальная сумма: {MIN_STARS} ⭐️\n"
        "💳 Способы выплаты:\n"
        "• Карта РФ (любого банка)\n"
        "• СБП по номеру телефона\n\n"
        "Преимущества:\n"
        "✅ Мгновенная оценка стоимости\n"
        "✅ Быстрые выплаты (5-15 минут)\n"
        "✅ Безопасные сделки\n"
        "✅ Работаем 24/7\n\n"
        "Выберите нужное действие ниже 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton("💫 Продать звёзды", callback_data='sell')],
        [InlineKeyboardButton("📋 Как проходит сделка?", callback_data='how_it_works')],
        [InlineKeyboardButton("🆘 Поддержка и контакты", callback_data='support')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_with_photo(update.effective_chat.id, welcome_text, reply_markup, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'sell':
        await start_selling(query, context)
    elif query.data == 'how_it_works':
        await show_instructions(query, context)
    elif query.data == 'support':
        await show_support(query, context)
    elif query.data == 'payment_rub':
        await select_payment_rub(query, context)
    elif query.data == 'payment_sbp':
        await select_payment_sbp(query, context)
    elif query.data == 'back_to_main':
        await back_to_main(query, context)
    elif query.data == 'back_to_amount':
        await back_to_amount(query, context)
    elif query.data == 'confirm_deal':
        await create_stars_invoice(query, context)
    elif query.data == 'reject_deal':
        await reject_deal(query, context)

async def start_selling(query, context):
    context.user_data['state'] = 'waiting_for_amount'
    
    text = (
        "💫 Сколько звёзд вы хотите продать?\n\n"
        f"💰 Курс обмена: 1 звезда = {STARS_TO_RUB} ₽\n"
        f"📊 Минимальная сумма для продажи: {MIN_STARS} ⭐️\n"
        f"📈 Максимальная сумма: не ограничена\n\n"
        "📝 Пожалуйста, введите количество звёзд (только число)\n"
        "• Используйте цифры, без пробелов и точек\n"
        "• Например: 1, 2, 5, 10, 100\n\n"
        f"✨ Пример: если введёте {MIN_STARS}, то получите {MIN_STARS * STARS_TO_RUB} ₽\n\n"
        "👇 Введите число ниже:"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await edit_message(query, text, reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    current_state = context.user_data.get('state')
    
    if current_state == 'waiting_for_amount':
        await handle_stars_amount(update, context)
    elif current_state == 'awaiting_details':
        await handle_payment_details(update, context)

async def handle_stars_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_text = update.message.text.strip()
    
    try:
        stars_amount = int(amount_text)
        if stars_amount <= 0:
            raise ValueError("Количество должно быть положительным")
        
        if stars_amount < MIN_STARS:
            text = (
                f"❌ Ошибка: минимальная сумма - {MIN_STARS} ⭐️!\n\n"
                f"Вы ввели: {stars_amount} ⭐️\n"
                f"Это меньше допустимого минимума.\n\n"
                "📝 Пожалуйста, введите сумму не меньше минимальной:\n"
                f"• Минимум: {MIN_STARS} ⭐️\n"
                f"• Пример: {MIN_STARS}, 2, 5\n\n"
                "👇 Попробуйте снова:"
            )
            
            keyboard = [[InlineKeyboardButton("◀️ В главное меню", callback_data='back_to_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await send_with_photo(update.effective_chat.id, text, reply_markup, context)
            return
            
    except ValueError:
        text = (
            "❌ Неправильный формат!\n\n"
            "Пожалуйста, введите количество звёзд только цифрами.\n\n"
            "📝 Примеры правильного ввода:\n"
            f"• {MIN_STARS}\n"
            "• 2\n"
            "• 5\n"
            "• 10\n"
            "• 100\n\n"
            "👇 Попробуйте снова:"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ В главное меню", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_with_photo(update.effective_chat.id, text, reply_markup, context)
        return
    
    rub_amount = round(stars_amount * STARS_TO_RUB)
    
    context.user_data['stars_amount'] = stars_amount
    context.user_data['rub_amount'] = rub_amount
    
    text = (
        "✅ Расчёт выполнен успешно!\n\n"
        f"💫 Количество звёзд: {stars_amount:,} ⭐️\n"
        f"💰 Сумма к выплате: {rub_amount:,} ₽\n"
        f"📊 Курс обмена: 1 ⭐️ = {STARS_TO_RUB} ₽\n\n"
        "Выберите способ получения оплаты:\n\n"
        "💳 Доступные варианты:\n"
        "• Карта РФ (любого банка)\n"
        "• СБП (по номеру телефона)\n\n"
        "👇 Нажмите на нужный вариант:"
    )
    
    keyboard = [
        [InlineKeyboardButton("💳 Карта РФ (любого банка)", callback_data='payment_rub')],
        [InlineKeyboardButton("📱 СБП (по номеру телефона)", callback_data='payment_sbp')],
        [InlineKeyboardButton("🔄 Ввести другую сумму", callback_data='sell')],
        [InlineKeyboardButton("❌ Отменить продажу", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_with_photo(update.effective_chat.id, text, reply_markup, context)
    context.user_data['state'] = 'awaiting_payment'

async def select_payment_rub(query, context):
    context.user_data['payment_method'] = 'rub'
    context.user_data['payment_name'] = '💳 Карта РФ'
    context.user_data['state'] = 'awaiting_details'
    
    stars_amount = context.user_data.get('stars_amount')
    rub_amount = context.user_data.get('rub_amount')
    
    text = (
        f"💳 Выбран способ оплаты: Карта РФ\n\n"
        f"💫 Количество звёзд: {stars_amount:,} ⭐️\n"
        f"💰 Сумма к выплате: {rub_amount:,} ₽\n\n"
        "📝 Пожалуйста, введите номер карты для получения оплаты:\n\n"
        "Требования к номеру карты:\n"
        "• 16 цифр\n"
        "• Можно вводить с пробелами или без\n"
        "• Подходят карты любых российских банков\n\n"
        "✅ Примеры правильного ввода:\n"
        "• 2200 1234 5678 9012\n"
        "• 2200123456789012\n"
        "• 4276 1234 5678 9012\n\n"
        "👇 Введите номер карты:"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад к выбору способа", callback_data='sell')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await edit_message(query, text, reply_markup)

async def select_payment_sbp(query, context):
    context.user_data['payment_method'] = 'sbp'
    context.user_data['payment_name'] = '📱 СБП'
    context.user_data['state'] = 'awaiting_details'
    
    stars_amount = context.user_data.get('stars_amount')
    rub_amount = context.user_data.get('rub_amount')
    
    text = (
        f"📱 Выбран способ оплаты: СБП\n\n"
        f"💫 Количество звёзд: {stars_amount:,} ⭐️\n"
        f"💰 Сумма к выплате: {rub_amount:,} ₽\n\n"
        "📝 Пожалуйста, введите номер телефона для получения оплаты через СБП:\n\n"
        "Требования к номеру:\n"
        "• Российский номер (МТС, Билайн, Мегафон, Tele2 и др.)\n"
        "• 11 цифр\n"
        "• Можно вводить в любом формате\n\n"
        "✅ Примеры правильного ввода:\n"
        "• 89991234567\n"
        "• +79991234567\n"
        "• 8 (999) 123-45-67\n\n"
        "👇 Введите номер телефона:"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад к выбору способа", callback_data='sell')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await edit_message(query, text, reply_markup)

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text.strip()
    payment_method = context.user_data.get('payment_method')
    payment_name = context.user_data.get('payment_name')
    
    if payment_method == 'rub':
        clean_details = details.replace(' ', '')
        if not clean_details.isdigit() or len(clean_details) != 16:
            text = (
                "❌ Неверный формат номера карты!\n\n"
                "Номер карты должен содержать 16 цифр.\n\n"
                "✅ Примеры правильного ввода:\n"
                "• 2200 1234 5678 9012\n"
                "• 2200123456789012\n\n"
                "📝 Проверьте введённые данные и попробуйте снова:\n"
                f"Вы ввели: {details}\n\n"
                "👇 Введите номер карты ещё раз:"
            )
            
            keyboard = [[InlineKeyboardButton("◀️ Назад к выбору способа", callback_data='sell')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await send_with_photo(update.effective_chat.id, text, reply_markup, context)
            return
    
    elif payment_method == 'sbp':
        clean_details = re.sub(r'\D', '', details)
        if len(clean_details) != 11 or not (clean_details.startswith('7') or clean_details.startswith('8')):
            text = (
                "❌ Неверный формат номера телефона!\n\n"
                "Введите российский номер телефона.\n\n"
                "✅ Примеры правильного ввода:\n"
                "• 89991234567\n"
                "• +79991234567\n"
                "• 8 (999) 123-45-67\n\n"
                "📝 Проверьте введённые данные и попробуйте снова:\n"
                f"Вы ввели: {details}\n\n"
                "👇 Введите номер телефона ещё раз:"
            )
            
            keyboard = [[InlineKeyboardButton("◀️ Назад к выбору способа", callback_data='sell')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await send_with_photo(update.effective_chat.id, text, reply_markup, context)
            return
    
    context.user_data['payment_details'] = details
    
    stars_amount = context.user_data.get('stars_amount')
    rub_amount = context.user_data.get('rub_amount')
    
    text = (
        "📋 Проверьте введённые данные:\n\n"
        f"💫 Количество звёзд: {stars_amount:,} ⭐️\n"
        f"💰 Сумма к выплате: {rub_amount:,} ₽\n"
        f"💳 Способ оплаты: {payment_name}\n"
        f"📝 Реквизиты: {details}\n\n"
        "⚠️ Пожалуйста, внимательно проверьте реквизиты!\n"
        "Отправка на неверные реквизиты может задержать выплату.\n\n"
        "✅ Всё верно?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Да, всё верно. Создать счёт на оплату", callback_data='confirm_deal')],
        [InlineKeyboardButton("❌ Нет, ввести заново", callback_data='sell')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_with_photo(update.effective_chat.id, text, reply_markup, context)
    context.user_data['state'] = 'awaiting_confirmation'

async def create_stars_invoice(query, context):
    stars_amount = context.user_data.get('stars_amount')
    rub_amount = context.user_data.get('rub_amount')
    payment_method = context.user_data.get('payment_method')
    payment_name = context.user_data.get('payment_name')
    payment_details = context.user_data.get('payment_details')
    
    data = load_data()
    transaction_id = len(data["transactions"]) + 1
    
    transaction = {
        "id": transaction_id,
        "user_id": query.from_user.id,
        "username": query.from_user.username,
        "stars_amount": stars_amount,
        "rub_amount": rub_amount,
        "payment_method": payment_method,
        "payment_name": payment_name,
        "payment_details": payment_details,
        "status": "invoice_created",
        "created_at": datetime.now().isoformat()
    }
    data["transactions"].append(transaction)
    save_data(data)
    
    title = f"Продажа {stars_amount} ⭐️"
    description = (
        f"Продажа {stars_amount} звёзд\n"
        f"Сумма к выплате: {rub_amount} ₽\n"
        f"Способ получения: {payment_name}\n"
        f"Реквизиты: {payment_details}"
    )
    
    payload = f"sale_{transaction_id}"
    prices = [LabeledPrice(label=f"{stars_amount} ⭐️", amount=stars_amount)]
    
    try:
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=prices
        )
        await query.message.delete()
    except Exception as e:
        logger.error(f"Ошибка при создании счёта: {e}")
        await query.edit_message_text(
            "❌ Ошибка при создании счёта\n\n"
            f"🆘 Поддержка: @{MANAGER_USERNAME}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ В главное меню", callback_data='back_to_main')
            ]])
        )

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    transaction_id = int(payload.replace('sale_', ''))
    
    data = load_data()
    transaction = None
    for t in data["transactions"]:
        if t["id"] == transaction_id:
            transaction = t
            break
    
    if transaction:
        for t in data["transactions"]:
            if t["id"] == transaction_id:
                t["status"] = "paid"
                t["paid_at"] = datetime.now().isoformat()
                break
        save_data(data)
        
        text = (
            "✅ Оплата получена!\n\n"
            f"💫 Звёзд переведено: {transaction['stars_amount']} ⭐️\n"
            f"💰 Сумма к выплате: {transaction['rub_amount']} ₽\n"
            f"💳 Способ выплаты: {transaction['payment_name']}\n"
            f"📝 На реквизиты: {transaction['payment_details']}\n\n"
            f"👨‍💼 Менеджер @{MANAGER_USERNAME} уже получил уведомление "
            f"и скоро переведёт оплату.\n\n"
            f"⏱ Ожидаемое время выплаты: 5-15 минут\n\n"
            f"Спасибо за сотрудничество! 🌟"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_with_photo(update.effective_chat.id, text, reply_markup, context)

async def reject_deal(query, context):
    text = "❌ Сделка отменена\n\n👇 Нажмите кнопку ниже, чтобы вернуться в главное меню:"
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await edit_message(query, text, reply_markup)
    context.user_data.clear()

async def back_to_amount(query, context):
    context.user_data['state'] = 'waiting_for_amount'
    text = (
        "💫 Сколько звёзд вы хотите продать?\n\n"
        f"💰 Курс обмена: 1 звезда = {STARS_TO_RUB} ₽\n"
        f"📊 Минимальная сумма для продажи: {MIN_STARS} ⭐️\n\n"
        "📝 Введите количество звёзд (только число)\n"
        f"✅ Пример: {MIN_STARS}\n\n"
        "👇 Введите число ниже:"
    )
    keyboard = [[InlineKeyboardButton("◀️ В главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await edit_message(query, text, reply_markup)

async def show_instructions(query, context):
    instructions = (
        "📋 Как проходит сделка:\n\n"
        "Шаг 1️⃣ - Введите количество звёзд для продажи\n"
        f"• Минимальная сумма: {MIN_STARS} ⭐️\n"
        f"• Курс: 1 ⭐️ = {STARS_TO_RUB} ₽\n\n"
        "Шаг 2️⃣ - Выберите способ получения оплаты\n"
        "• Карта РФ (любого банка)\n"
        "• СБП по номеру телефона\n\n"
        "Шаг 3️⃣ - Введите реквизиты для выплаты\n"
        "• Номер карты (16 цифр)\n"
        "• Или номер телефона для СБП\n\n"
        "Шаг 4️⃣ - Подтвердите создание счёта\n"
        "• Проверьте все введённые данные\n\n"
        "Шаг 5️⃣ - Оплатите счёт звёздами\n"
        "• Нажмите кнопку «Оплатить»\n"
        "• Подтвердите перевод в окне Telegram\n\n"
        "Шаг 6️⃣ - Получите выплату\n"
        f"• Менеджер @{MANAGER_USERNAME} проверит оплату\n"
        "• Деньги поступят на ваши реквизиты\n\n"
        f"⏱ Среднее время сделки: 5-15 минут\n\n"
        "✅ Гарантируем быстрые и безопасные сделки!"
    )
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await edit_message(query, instructions, reply_markup)

async def show_support(query, context):
    support_text = (
        "🆘 Поддержка и контакты\n\n"
        f"👨‍💼 Менеджер: @{MANAGER_USERNAME}\n\n"
        "По всем вопросам обращайтесь:\n"
        "• Вопросы по сделкам\n"
        "• Проблемы с оплатой\n"
        "• Технические неполадки\n"
        "• Сотрудничество\n\n"
        "⏰ Время работы: 24/7, без выходных\n\n"
        "📊 Среднее время ответа: 5-10 минут\n\n"
        "⚠️ Важно!\n"
        "• Все сделки проводятся только через этого бота\n"
        "• Не переводите звёзды на другие аккаунты\n"
        "• Не доверяйте сторонним лицам\n\n"
        "💬 Напишите менеджеру - поможем с любым вопросом!"
    )
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await edit_message(query, support_text, reply_markup)

async def back_to_main(query, context):
    context.user_data.clear()
    user = query.from_user
    first_name = user.first_name
    
    welcome_text = (
        f"🌟 С возвращением, {first_name}!\n\n"
        "Мы профессионально покупаем Telegram Stars по самому выгодному курсу!\n\n"
        f"💰 Курс обмена: 1 звезда = {STARS_TO_RUB} ₽\n"
        f"📊 Минимальная сумма: {MIN_STARS} ⭐️\n"
        "💳 Способы выплаты:\n"
        "• Карта РФ (любого банка)\n"
        "• СБП по номеру телефона\n\n"
        "Преимущества:\n"
        "✅ Мгновенная оценка стоимости\n"
        "✅ Быстрые выплаты (5-15 минут)\n"
        "✅ Безопасные сделки\n"
        "✅ Работаем 24/7\n\n"
        "Выберите нужное действие ниже 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton("💫 Продать звёзды", callback_data='sell')],
        [InlineKeyboardButton("📋 Как проходит сделка?", callback_data='how_it_works')],
        [InlineKeyboardButton("🆘 Поддержка и контакты", callback_data='support')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await edit_message(query, welcome_text, reply_markup)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return
    
    data = load_data()
    total_users = len(data["users"])
    total_transactions = len(data["transactions"])
    invoice_created = sum(1 for t in data["transactions"] if t["status"] == "invoice_created")
    paid = sum(1 for t in data["transactions"] if t["status"] == "paid")
    total_stars = sum(t.get("stars_amount", 0) for t in data["transactions"])
    total_rub = sum(t.get("rub_amount", 0) for t in data["transactions"])
    
    stats = (
        f"📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📦 Всего транзакций: {total_transactions}\n"
        f"⏳ Создано счетов: {invoice_created}\n"
        f"✅ Оплачено: {paid}\n"
        f"💫 Всего звёзд куплено: {total_stars:,} ⭐️\n"
        f"💰 Всего выплачено: {total_rub:,} ₽"
    )
    
    await update.message.reply_text(stats)

def main():
    print("=" * 60)
    print("ЗАПУСК БОТА ДЛЯ СКУПКИ ЗВЁЗД TELEGRAM")
    print("=" * 60)
    print(f"Менеджер: @{MANAGER_USERNAME}")
    print(f"Курс: 1 звезда = {STARS_TO_RUB} ₽")
    print(f"Минимальная сумма: {MIN_STARS} ⭐️")
    print("=" * 60)
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
