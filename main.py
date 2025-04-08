import logging
import asyncio
import time
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os
from gpt import generate_prediction
from analytics import update_analytics_data  # Импортируем функции аналитики

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Создаём бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Хранилище данных в памяти
user_prompts = {}  # Хранит анкеты пользователей
user_predictions = {}  # Хранит прогнозы
processed_callbacks = set()  # Хранит обработанные callback_query_id
user_analytics = {}  # Хранит аналитику: {chat_id: {"start_count": int, "forecast_count": int, "payment_count": int, "start_time": float}}
user_start_times = {}  # Хранит время начала сессии: {chat_id: start_time}

# Максимальная длина сообщения в Telegram
TELEGRAM_MESSAGE_LIMIT = 4096

# Функция для разбиения текста на части
def split_text(text, limit=TELEGRAM_MESSAGE_LIMIT):
    parts = []
    while len(text) > limit:
        split_pos = text[:limit].rfind('\n')
        if split_pos == -1:
            split_pos = text[:limit].rfind(' ')
            if split_pos == -1:
                split_pos = limit
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    if text:
        parts.append(text)
    return parts

# Функция для обновления аналитики
async def log_analytics(chat_id, username, start_count=0, forecast_count=0, payment_count=0):
    if chat_id not in user_analytics:
        user_analytics[chat_id] = {
            "start_count": 0,
            "forecast_count": 0,
            "payment_count": 0,
            "start_time": user_start_times.get(chat_id, time.time())
        }
    
    user_analytics[chat_id]["start_count"] += start_count
    user_analytics[chat_id]["forecast_count"] += forecast_count
    user_analytics[chat_id]["payment_count"] += payment_count
    
    # Вычисляем время использования (в минутах)
    start_time = user_analytics[chat_id]["start_time"]
    usage_time = (time.time() - start_time) / 60  # Время в минутах
    
    # Обновляем данные в CSV
    update_analytics_data(
        username=username,
        user_id=chat_id,
        start_count=user_analytics[chat_id]["start_count"],
        forecast_count=user_analytics[chat_id]["forecast_count"],
        payment_count=user_analytics[chat_id]["payment_count"],
        usage_time=usage_time
    )

@dp.message(CommandStart())
async def start(message: types.Message):
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    
    # Сохраняем время начала сессии
    user_start_times[chat_id] = time.time()
    
    # Увеличиваем счётчик нажатий /start
    await log_analytics(chat_id, username, start_count=1)
    
    logging.info(f"Пользователь {chat_id} запустил бота")
    await message.answer(
        "🌟 <b>УЗНАЙ, ЧТО ЖДЁТ ТЕБЯ ЧЕРЕЗ 5 ЛЕТ!</b> 🌟\n\n"
        "Я помогу тебе заглянуть в будущее с помощью ИИ! Ответь на несколько вопросов о себе, и я создам подробный прогноз твоей жизни на 5 лет вперёд. А после ты сможешь узнать, что будет, если ничего не изменить, всего за 1 звезду ⭐! Это займёт всего пару минут! 😊\n\n"
        "Чтобы начать, просто заполни анкету ниже 👇"
    )
    await message.answer(
        "📝 <b>Давай познакомимся поближе!</b>\n\n"
        "Чтобы я мог сделать точный прогноз твоей жизни через 5 лет, мне нужно узнать о тебе немного больше. Скопируй это сообщение, заполни поля и отправь его мне обратно. Это просто! 😊\n\n"
        "1. Нажми на это сообщение и выбери \"Копировать\".\n"
        "2. Вставь его в поле ввода (долгое нажатие → \"Вставить\").\n"
        "3. Заполни свои ответы после каждого пункта.\n"
        "4. Отправь мне сообщение!\n\n"
        "Вот анкета:\n\n"
        "<i>Мой возраст: (например, 25)</i>\n"
        "<i>Страна, где я живу: (например, Россия)</i>\n"
        "<i>Семейное положение: (например, не женат/замужем)</i>\n"
        "<i>Мои 3-5 главных интересов: (например, путешествия, книги, спорт)</i>\n"
        "<i>Как я зарабатываю на жизнь: (например, работаю программистом)</i>\n"
        "<i>Как я забочусь о своём здоровье: (например, хожу в спортзал 2 раза в неделю)</i>\n"
        "<i>Моя рутина в жизни: (например, встаю в 7 утра, работаю до 18:00, вечером читаю)</i>\n"
        "<i>Моя самая большая мечта: (например, объездить весь мир)</i>\n\n"
        "<b>На основе этих данных я создам детальное описание моей жизни через 5 лет!</b>"
    )

# Обработчик анкеты
@dp.message(lambda message: not message.text.startswith('/'))
async def handle_filled_form(message: types.Message):
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    
    # Проверяем, что сообщение содержит ключевые слова анкеты
    if "Мой возраст" in message.text and "Страна, где я живу" in message.text:
        logging.info(f"Получена анкета от chat_id {chat_id}")
        user_prompts[chat_id] = message.text
        await message.answer("🧠 Анализирую твою жизнь... Это займёт всего несколько секунд! ⏳")
        try:
            result = await generate_prediction(message.text)
            user_predictions[chat_id] = result

            # Формируем сообщение
            full_message = (
                "<b>🔮 Твой прогноз на 5 лет вперёд:</b>\n\n"
                "Вот что ждёт тебя, если ты продолжишь идти текущим путём:\n\n"
                f"{result}"
            )

            # Разбиваем текст на части, если он слишком длинный
            message_parts = split_text(full_message, TELEGRAM_MESSAGE_LIMIT)

            # Отправляем каждую часть
            for part in message_parts:
                await message.answer(part)
                await asyncio.sleep(0.5)

            # Увеличиваем счётчик сгенерированных прогнозов
            await log_analytics(chat_id, username, forecast_count=1)
            
            logging.info(f"Прогноз успешно отправлен для chat_id {chat_id}")

            # Создаём кнопки
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Раскрыть 3 события за 1 звезду ✨", callback_data="learn_scenarios")],
                [InlineKeyboardButton(text="Поделиться прогнозом 📤", callback_data="share_prediction")],
                [InlineKeyboardButton(text="Попробовать снова 🔄", callback_data="try_again")]
            ])
            await message.answer(
                "💡 А что, если ничего не менять? Узнай, какие 3 ключевых события ждут тебя через 5 лет, если ты продолжишь идти тем же путём! Это может быть неожиданно... 😲",
                reply_markup=markup
            )
        except Exception as e:
            await message.answer(
                "К сожалению, не удалось сгенерировать прогноз. 😔 Возможно, текст слишком длинный. "
                "Попробуй сократить свои ответы в анкете и отправить её снова. Напиши /start, чтобы начать заново!"
            )
            logging.error(f"Ошибка при генерации прогноза для chat_id {chat_id}: {e}")
    # Оставляем обработчик секретного текста
    elif message.text == "секретнаяпокупка123":
        chat_id = message.chat.id
        logging.info(f"Секретная покупка для chat_id {chat_id}")
        user_input = user_prompts.get(chat_id)
        previous_result = user_predictions.get(chat_id)
        if not user_input:
            await message.answer(
                "Сначала заполни анкету! 😊\n"
                "Отправь /start, чтобы начать заново и заполнить анкету."
            )
            logging.warning(f"Анкета не найдена для chat_id: {chat_id}")
            return
        await message.answer("💫 Покупка успешна! Генерирую...")
        try:
            future = await generate_prediction(user_input, future_mode=True, previous_response=previous_result)
            message_parts = split_text(future, TELEGRAM_MESSAGE_LIMIT)
            for part in message_parts:
                await message.answer(part)
                await asyncio.sleep(0.5)
            await message.answer("Если хочешь попробовать другой сценарий, заполни анкету заново с помощью /start! 😊")
            
            # Увеличиваем счётчик оплат и сгенерированных прогнозов
            await log_analytics(chat_id, username, forecast_count=1, payment_count=1)
            
            logging.info(f"3 события успешно отправлены для chat_id {chat_id}")
        except Exception as e:
            await message.answer("Произошла ошибка при генерации событий. Пожалуйста, попробуй снова.")
            logging.error(f"Ошибка при генерации событий для chat_id {chat_id}: {e}")
    else:
        await message.answer(
            "Кажется, ты отправил что-то не то. 😅 Чтобы я мог сделать прогноз, пожалуйста, заполни анкету. Скопируй её, заполни свои данные и отправь мне обратно. Нажми /start, чтобы получить анкету снова!"
        )
        logging.warning(f"Сообщение от chat_id {chat_id} не распознано как анкета")

# Обработчик нажатия на кнопку "Раскрыть 3 события"
@dp.callback_query(lambda c: c.data == "learn_scenarios")
async def process_learn_scenarios(callback_query: types.CallbackQuery):
    callback_id = callback_query.id
    chat_id = callback_query.from_user.id
    username = callback_query.from_user.username or callback_query.from_user.first_name
    message_id = callback_query.message.message_id

    if callback_id in processed_callbacks:
        logging.info(f"Повторный callback {callback_id} от chat_id {chat_id}, игнорируем")
        await callback_query.answer("Счёт уже отправлен, пожалуйста, подожди! 😊")
        return

    processed_callbacks.add(callback_id)
    logging.info(f"Пользователь {chat_id} нажал на кнопку 'Раскрыть 3 события' (callback_id: {callback_id})")

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logging.info(f"Сообщение с кнопками (message_id: {message_id}) удалено для chat_id {chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при удалении сообщения для chat_id {chat_id}: {e}")

    await callback_query.message.answer(
        "Ты на шаге от того, чтобы узнать 3 ключевых события, которые ждут тебя через 5 лет, если ты не изменишь свой путь! 💡 Это может стать важным открытием для твоего будущего. Всего за 1 звезду ⭐ (валюта Telegram, которую ты можешь купить прямо здесь) я раскрою тебе эти события. Готов?"
    )

    try:
        await bot.send_invoice(
            chat_id=chat_id,
            title="3 события в будущем",
            description="Узнай, что произойдёт, если не изменишь сценарий.",
            payload="buy_3_events",
            provider_token="",
            currency="XTR",
            prices=[types.LabeledPrice(label="Прогноз", amount=1)],  # Изменяем цену на 1 звезду
        )
        logging.info(f"Счёт на 1 звезду отправлен для chat_id {chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при отправке счёта для chat_id {chat_id}: {str(e)} (тип ошибки: {type(e).__name__})")
        await callback_query.message.answer(
            "К сожалению, не удалось создать счёт. 😔 Возможно, Telegram Stars недоступны в твоём регионе. Пожалуйста, свяжись с поддержкой Telegram."
        )

    await callback_query.answer()

# Обработчик нажатия на кнопку "Поделиться прогнозом"
@dp.callback_query(lambda c: c.data == "share_prediction")
async def share_prediction(callback_query: types.CallbackQuery):
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logging.info(f"Сообщение с кнопками (message_id: {message_id}) удалено для chat_id {chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при удалении сообщения для chat_id {chat_id}: {e}")

    prediction = user_predictions.get(chat_id)
    if not prediction:
        await callback_query.message.answer("Прогноз не найден. Попробуй заполнить анкету заново с помощью /start!")
        logging.warning(f"Прогноз не найден для chat_id {chat_id}")
        return
    share_text = f"🔮 Мой прогноз на 5 лет вперёд от @LifeIn5Bot:\n\n{prediction}\n\nУзнай, что ждёт тебя: t.me/LifeIn5Bot"
    message_parts = split_text(share_text, TELEGRAM_MESSAGE_LIMIT)
    for part in message_parts:
        await callback_query.message.answer(
            part,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Поделиться", url=f"https://t.me/share/url?url={part}")]
            ])
        )
        await asyncio.sleep(0.5)
    await callback_query.answer()

# Обработчик нажатия на кнопку "Попробовать снова"
@dp.callback_query(lambda c: c.data == "try_again")
async def try_again(callback_query: types.CallbackQuery):
    chat_id = callback_query.from_user.id
    message_id = callback_query.message.message_id

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logging.info(f"Сообщение с кнопками (message_id: {message_id}) удалено для chat_id {chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при удалении сообщения для chat_id {chat_id}: {e}")

    user_prompts.pop(chat_id, None)
    user_predictions.pop(chat_id, None)
    await callback_query.message.answer(
        "Давай попробуем снова! Заполни анкету заново, чтобы получить новый прогноз. 😊"
    )
    await callback_query.message.answer(
        "📝 <b>Давай познакомимся поближе!</b>\n\n"
        "Чтобы я мог сделать точный прогноз твоей жизни через 5 лет, мне нужно узнать о тебе немного больше. Скопируй это сообщение, заполни поля и отправь его мне обратно. Это просто! 😊\n\n"
        "1. Нажми на это сообщение и выбери \"Копировать\".\n"
        "2. Вставь его в поле ввода (долгое нажатие → \"Вставить\").\n"
        "3. Заполни свои ответы после каждого пункта.\n"
        "4. Отправь мне сообщение!\n\n"
        "Вот анкета:\n\n"
        "<i>Мой возраст: (например, 25)</i>\n"
        "<i>Страна, где я живу: (например, Россия)</i>\n"
        "<i>Семейное положение: (например, не женат/замужем)</i>\n"
        "<i>Мои 3-5 главных интересов: (например, путешествия, книги, спорт)</i>\n"
        "<i>Как я зарабатываю на жизнь: (например, работаю программистом)</i>\n"
        "<i>Как я забочусь о своём здоровье: (например, хожу в спортзал 2 раза в неделю)</i>\n"
        "<i>Моя рутина в жизни: (например, встаю в 7 утра, работаю до 18:00, вечером читаю)</i>\n"
        "<i>Моя самая большая мечта: (например, объездить весь мир)</i>\n\n"
        "<b>На основе этих данных я создам детальное описание моей жизни через 5 лет!</b>"
    )
    await callback_query.answer()

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    logging.info(f"Получен pre_checkout_query: {pre_checkout_query.id}")
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda message: message.successful_payment)
async def process_successful_payment(message: types.Message):
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    logging.info(f"Начало обработки успешной оплаты для chat_id {chat_id}")

    # Логируем полное содержимое message.successful_payment
    logging.info(f"Полное содержимое successful_payment: {message.successful_payment}")

    payload = message.successful_payment.invoice_payload
    logging.info(f"Получена успешная оплата с payload: {payload}")

    if payload == "buy_3_events":
        logging.info(f"Payload совпадает, начинаем обработку для chat_id {chat_id}")
        user_input = user_prompts.get(chat_id)
        previous_result = user_predictions.get(chat_id)
        logging.info(f"Получены user_input: {user_input is not None}, previous_result: {previous_result is not None}")

        if not user_input:
            logging.warning(f"Анкета не найдена для chat_id: {chat_id}")
            await message.answer("Сначала заполни анкету! Нажми /start, чтобы начать заново.")
            return

        await message.answer("💫 Покупка успешна! Генерирую твои 3 ключевых события... ⏳")
        logging.info(f"Сообщение о начале генерации отправлено для chat_id {chat_id}")

        try:
            future = await generate_prediction(user_input, future_mode=True, previous_response=previous_result)
            logging.info(f"Прогноз успешно сгенерирован для chat_id {chat_id}")

            message_parts = split_text(future, TELEGRAM_MESSAGE_LIMIT)
            for part in message_parts:
                await message.answer(part)
                await asyncio.sleep(0.5)
            await message.answer("Если хочешь попробовать другой сценарий, заполни анкету заново с помощью /start! 😊")
            
            # Увеличиваем счётчик оплат и сгенерированных прогнозов
            await log_analytics(chat_id, username, forecast_count=1, payment_count=1)
            
            logging.info(f"3 события успешно отправлены для chat_id {chat_id}")
        except Exception as e:
            logging.error(f"Ошибка при генерации событий для chat_id {chat_id}: {e}")
            await message.answer("Произошла ошибка при генерации событий. Пожалуйста, попробуй снова.")
    else:
        logging.warning(f"Неизвестный payload: {payload} для chat_id {chat_id}")
        await message.answer("Произошла ошибка: неизвестный тип оплаты. Пожалуйста, свяжись с поддержкой.")

# Обработчик для отладки необработанных сообщений
@dp.message()
async def debug_unhandled(message: types.Message):
    logging.info(f"Необработанное сообщение: {message.text} от chat_id {message.chat.id}")

async def main():
    print("🚀 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
