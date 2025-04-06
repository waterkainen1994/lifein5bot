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
        "🙋 <b>ЭТО ЖДЁТ ТЕБЯ ЧЕРЕЗ 5 ЛЕТ</b> 🥲\n\n"
        "Всего 3 вопроса и ИИ построит прогноз твоей жизни на 5 лет вперёд 👏\n"
        "Нажми 'Запустить', чтобы начать!"
    )
    await message.answer(
        "Пожалуйста, скопируй это сообщение, заполни поля про себя честно и отправь мне его обратно:\n\n"
        "<i>Мой возраст:</i>\n"
        "<i>Страна, где я живу:</i>\n"
        "<i>Семейное положение:</i>\n"
        "<i>Мои 3-5 главных интересов:</i>\n"
        "<i>Как я зарабатываю на жизнь:</i>\n"
        "<i>Как я забочусь о своём здоровье:</i>\n"
        "<i>Моя рутина в жизни:</i>\n"
        "<i>Моя самая большая мечта:</i>\n\n"
        "<b>На основе этих данных создай детальное описание моей жизни через 5 лет.</b>"
    )

# Обработчик анкеты
@dp.message(lambda message: not message.text.startswith('/'))
async def handle_filled_form(message: types.Message):
    chat_id = message.chat.id
    # Проверяем, что сообщение содержит ключевые слова анкеты
    if "Мой возраст" in message.text and "Страна, где я живу" in message.text:
        logging.info(f"Получена анкета от chat_id {chat_id}")
        user_prompts[chat_id] = message.text
        await message.answer("🧠 Анализирую твою жизнь...")
        try:
            result = await generate_prediction(message.text)
            user_predictions[chat_id] = result
            await message.answer(f"<b>🔮 Прогноз:</b>\n{result}")
            logging.info(f"Прогноз успешно отправлен для chat_id {chat_id}")

            # Создаём кнопку "Узнать про сценарии"
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Узнать про сценарии", callback_data="learn_scenarios")]
            ])
            await message.answer("Хочешь узнать, что будет, если ты не изменишь сценарий?", reply_markup=markup)
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
            await message.answer("Мы работаем над улучшением данного бота, ждите обновлений! 🚀")
            logging.info(f"3 события успешно отправлены для chat_id {chat_id}")
        except Exception as e:
            await message.answer("Произошла ошибка при генерации событий. Пожалуйста, попробуй снова.")
            logging.error(f"Ошибка при генерации событий для chat_id {chat_id}: {e}")
    else:
        await message.answer("Пожалуйста, заполни анкету, скопировав и заполнив предложенный шаблон.")
        logging.warning(f"Сообщение от chat_id {chat_id} не распознано как анкета")

# Обработчик нажатия на кнопку "Узнать про сценарии"
@dp.callback_query(lambda c: c.data == "learn_scenarios")
async def process_learn_scenarios(callback_query: types.CallbackQuery):
    chat_id = callback_query.from_user.id
    await callback_query.message.answer(
        "Чтобы узнать, что произойдёт, если ты не изменишь сценарий, необходимо оплатить 1 звёзду."
    )
    await bot.send_invoice(
        chat_id=chat_id,
        title="3 события в будущем",
        description="Узнай, что произойдёт, если не изменишь сценарий.",
        payload="buy_3_events",
        provider_token="",
        currency="XTR",
        prices=[types.LabeledPrice(label="Прогноз", amount=1)],
    )
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
            await message.answer("Сначала заполни анкету!")
            logging.warning(f"Анкета не найдена для chat_id: {chat_id}")
            return
        await message.answer("💫 Покупка успешна! Генерирую...")
        try:
            future = await generate_prediction(user_input, future_mode=True, previous_response=previous_result)
            await message.answer(future)
            await message.answer("Мы работаем над улучшением данного бота, ждите обновлений! 🚀")
            logging.info(f"3 события успешно отправлены для chat_id {chat_id}")
        except Exception as e:
            await message.answer("Произошла ошибка при генерации событий. Пожалуйста, попробуй снова.")
            logging.error(f"Ошибка при генерации событий для chat_id {chat_id}: {e}")

@dp.message()
async def debug_unhandled(message: types.Message):
    logging.info(f"Необработанное сообщение: {message.text} от chat_id {message.chat.id}")

async def main():
    print("🚀 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
