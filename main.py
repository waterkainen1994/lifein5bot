import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os
from gpt import generate_prediction

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

@dp.message(CommandStart())
async def start(message: types.Message):
    chat_id = message.chat.id
    logging.info(f"Пользователь {chat_id} запустил бота")
    await message.answer(
        "🌟 <b>УЗНАЙ, ЧТО ЖДЁТ ТЕБЯ ЧЕРЕЗ 5 ЛЕТ!</b> 🌟\n\n"
        "Я помогу тебе заглянуть в будущее с помощью ИИ! Ответь на несколько вопросов о себе, и я создам подробный прогноз твоей жизни на 5 лет вперёд. Это займёт всего пару минут! 😊\n\n"
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
        "<b>На основе этих данных я создам детальное описание твоей жизни через 5 лет!</b>"
    )

# Обработчик анкеты
@dp.message(lambda message: not message.text.startswith('/'))
async def handle_filled_form(message: types.Message):
    chat_id = message.chat.id
    # Проверяем, что сообщение содержит ключевые слова анкеты
    if "Мой возраст" in message.text and "Страна, где я живу" in message.text:
        logging.info(f"Получена анкета от chat_id {chat_id}")
        user_prompts[chat_id] = message.text
        await message.answer("🧠 Анализирую твою жизнь... Это займёт всего несколько секунд! ⏳")
        try:
            result = await generate_prediction(message.text)
            user_predictions[chat_id] = result
            await message.answer(
                "<b>🔮 Твой прогноз на 5 лет вперёд:</b>\n\n"
                "Вот что ждёт тебя, если ты продолжишь идти текущим путём:\n\n"
                f"{result}"
            )
            logging.info(f"Прогноз успешно отправлен для chat_id {chat_id}")

            # Создаём кнопку "Узнать про сценарии"
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Узнать 3 события за 1 звезду ⭐", callback_data="learn_scenarios")]
            ])
            await message.answer(
                "Хочешь узнать, что произойдёт, если ты не изменишь свой текущий путь? Я расскажу тебе о 3 ключевых событиях, которые могут случиться в твоей жизни через 5 лет, если всё останется как есть.",
                reply_markup=markup
            )
        except Exception as e:
            await message.answer("Произошла ошибка при генерации прогноза. Пожалуйста, попробуй снова.")
            logging.error(f"Ошибка при генерации прогноза для chat_id {chat_id}: {e}")
    # Добавляем обработчик секретного текста для тестовой покупки
    elif message.text == "секретнаяпокупка123":  # Секретный текст
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
            await message.answer(future)
            await message.answer("Если хочешь попробовать другой сценарий, заполни анкету заново с помощью /start! 😊")
            logging.info(f"3 события успешно отправлены для chat_id {chat_id}")
        except Exception as e:
            await message.answer("Произошла ошибка при генерации событий. Пожалуйста, попробуй снова.")
            logging.error(f"Ошибка при генерации событий для chat_id {chat_id}: {e}")
    else:
        await message.answer(
            "Кажется, ты отправил что-то не то. 😅 Чтобы я мог сделать прогноз, пожалуйста, заполни анкету. Скопируй её, заполни свои данные и отправь мне обратно. Нажми /start, чтобы получить анкету снова!"
        )
        logging.warning(f"Сообщение от chat_id {chat_id} не распознано как анкета")

# Обработчик нажатия на кнопку "Узнать про сценарии"
@dp.callback_query(lambda c: c.data == "learn_scenarios")
async def process_learn_scenarios(callback_query: types.CallbackQuery):
    chat_id = callback_query.from_user.id
    logging.info(f"Пользователь {chat_id} нажал на кнопку 'Узнать про сценарии'")
    await callback_query.message.answer(
        "Чтобы узнать 3 ключевых события, которые ждут тебя через 5 лет, если ты не изменишь свой путь, нужно оплатить 1 звезду ⭐. Это валюта Telegram, которую ты можешь купить прямо здесь. Готов?"
    )
    try:
        await bot.send_invoice(
            chat_id=chat_id,
            title="3 события в будущем",
            description="Узнай, что произойдёт, если не изменишь сценарий.",
            payload="buy_3_events",
            currency="XTR",
            prices=[types.LabeledPrice(label="Прогноз", amount=1)],
        )
        logging.info(f"Счёт на 1 звезду отправлен для chat_id {chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при отправке счёта для chat_id {chat_id}: {e}")
        await callback_query.message.answer("Произошла ошибка при создании счёта. Попробуй снова позже.")
    await callback_query.answer()

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    logging.info(f"Получен pre_checkout_query: {pre_checkout_query.id}")
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda message: message.successful_payment)
async def process_successful_payment(message: types.Message):
    chat_id = message.chat.id
    payload = message.successful_payment.invoice_payload
    logging.info(f"Получена успешная оплата: {payload}")
    
    if payload == "buy_3_events":
        user_input = user_prompts.get(chat_id)
        previous_result = user_predictions.get(chat_id)
        if not user_input:
            await message.answer("Сначала заполни анкету! Нажми /start, чтобы начать заново.")
            logging.warning(f"Анкета не найдена для chat_id: {chat_id}")
            return
        await message.answer("💫 Покупка успешна! Генерирую твои 3 ключевых события... ⏳")
        try:
            future = await generate_prediction(user_input, future_mode=True, previous_response=previous_result)
            await message.answer(
                "<b>Вот что может произойти, если ты не изменишь свой путь:</b>\n\n"
                f"{future}"
            )
            await message.answer("Если хочешь попробовать другой сценарий, заполни анкету заново с помощью /start! 😊")
            logging.info(f"3 события успешно отправлены для chat_id {chat_id}")
        except Exception as e:
            await message.answer("Произошла ошибка при генерации событий. Пожалуйста, попробуй снова.")
            logging.error(f"Ошибка при генерации событий для chat_id {chat_id}: {e}")

# Обработчик для отладки необработанных сообщений
@dp.message()
async def debug_unhandled(message: types.Message):
    logging.info(f"Необработанное сообщение: {message.text} от chat_id {message.chat.id}")

async def main():
    print("🚀 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
