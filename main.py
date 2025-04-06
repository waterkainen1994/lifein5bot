import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from gpt import generate_prediction

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

logger.info("Starting bot initialization...")

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверяем, что переменные окружения загружены
if not BOT_TOKEN:
    logger.error("BOT_TOKEN is not set. Please check your environment variables.")
    raise ValueError("BOT_TOKEN is not set")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY is not set. Please check your environment variables.")
    raise ValueError("OPENAI_API_KEY is not set")

logger.info("Environment variables loaded successfully")

# Создаём бота
try:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    logger.info("Bot initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
    raise

dp = Dispatcher()
logger.info("Dispatcher initialized")

# Хранилище данных в памяти
user_prompts = {}  # Хранит анкеты пользователей
user_predictions = {}  # Хранит прогнозы

@dp.message(CommandStart())
async def start(message: types.Message):
    chat_id = message.chat.id
    logger.info(f"Пользователь {chat_id} запустил бота")
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
        logger.info(f"Получена анкета от chat_id {chat_id}")
        user_prompts[chat_id] = message.text
        await message.answer("🧠 Анализирую твою жизнь...")
        try:
            result = await generate_prediction(message.text)
            user_predictions[chat_id] = result
            await message.answer(f"<b>🔮 Прогноз:</b>\n{result}")
            logger.info(f"Прогноз успешно отправлен для chat_id {chat_id}")

            # Создаём кнопку "Узнать про сценарии"
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Узнать про сценарии", callback_data="learn_scenarios")]
            ])
            await message.answer("Хочешь узнать, что будет, если ты не изменишь сценарий?", reply_markup=markup)
        except Exception as e:
            await message.answer("Произошла ошибка при генерации прогноза. Пожалуйста, попробуй снова.")
            logger.error(f"Ошибка при генерации прогноза для chat_id {chat_id}: {e}")
    # Добавляем обработчик секретного текста для тестовой покупки
    elif message.text == "секретнаяпокупка123":  # Секретный текст
        chat_id = message.chat.id
        logger.info(f"Секретная покупка для chat_id {chat_id}")
        user_input = user_prompts.get(chat_id)
        previous_result = user_predictions.get(chat_id)
        if not user_input:
            await message.answer(
                "Сначала заполни анкету! 😊\n"
                "Отправь /start, чтобы начать заново и заполнить анкету."
            )
            logger.warning(f"Анкета не найдена для chat_id: {chat_id}")
            return
        await message.answer("💫 Покупка успешна! Генерирую...")

# Основной цикл бота
async def main():
    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot)
        logger.info("Polling started successfully")
    except Exception as e:
        logger.error(f"Error during polling: {e}")
        raise

if __name__ == "__main__":
    logger.info("Running main function...")
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Failed to run bot: {e}")
        raise