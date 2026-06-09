import asyncio
import logging
import random
import time
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import BOT_TOKEN, BOT_USERNAME, CHANNEL_ID, ADMIN_ID, PORT
import database as db
import ai_engine as ai

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_states = {}
chat_cooldowns = {}
START_TIME = time.time()

# ==========================
# [WEB] ВЕБ-СЕРВЕР ДЛЯ UPTIMEROBOT
# ==========================
async def handle_health(request):
    uptime_hours = (time.time() - START_TIME) / 3600
    text = f"[OK] Bot is running! Uptime: {uptime_hours:.1f}h"
    return web.Response(text=text, status=200, content_type='text/plain')

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"[WEB] Server started on port {PORT}")
    return runner

@dp.startup()
async def on_startup():
    await db.init_db()
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[OK] AlphaVods Bot started! Time: {current_time}")

@dp.shutdown()
async def on_shutdown():
    print("[INFO] Bot is shutting down...")
    await bot.session.close()    print("[OK] Bot session closed")

# ==========================
# [DM] ЛИЧКА: ОБУЧЕНИЕ
# ==========================
@dp.message(Command("start"), F.chat.type == "private")
async def start_private(message: types.Message):
    await db.save_user(message.from_user.id, message.from_user.username)
    uptime_hours = (time.time() - START_TIME) / 3600
    await message.answer(
        f"Здарова! Я свой в доску бот для Альфоводов. 🏍\n"
        f"Работаю уже {uptime_hours:.1f} часов без зависаний!\n"
        f"Хочешь научить меня понимать вас? Напиши /train"
    )

@dp.message(Command("train"), F.chat.type == "private")
async def train_start(message: types.Message):
    user_states[message.from_user.id] = {"step": "ask_nickname"}
    await message.answer("Окей, давай знакомиться. Какая у тебя кличка в тусовке?")

@dp.message(Command("places"), F.chat.type == "private")
async def show_places(message: types.Message):
    places = await db.get_all_places()
    if not places:
        await message.answer("Пока нет сохранённых мест. Кидай геолокации в чат!")
        return
    text = "📍 **Сохранённые места:**\n\n"
    for name, lat, lon, type_place in places:
        text += f"• {name} ({type_place})\n"
        text += f"  [Открыть на карте](https://maps.google.com/?q={lat},{lon})\n\n"
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

@dp.message(F.chat.type == "private")
async def private_chat_handler(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if not state:
        await message.answer(
            "Если хочешь меня обучить, жми /train 😉\n"
            "Или жми /post, чтобы сделать пост в канал.\n"
            "Напиши /places — покажу все сохранённые точки."
        )
        return

    if state["step"] == "ask_nickname":
        await db.update_user_field(user_id, "nickname", message.text)
        user_states[user_id]["step"] = "ask_bike"
        await message.answer(f"Записал: {message.text} 🔥\nНа чем гоняешь? (Модель, цвет, что тюнинговал)")
            elif state["step"] == "ask_bike":
        await db.update_user_field(user_id, "bike", message.text)
        user_states[user_id]["step"] = "done"
        await message.answer("Понял, запомнил! Теперь я знаю, кто ты и на чем катаешь. В чате буду узнавать! ✌️")
        del user_states[user_id]

# ==========================
# [GROUP] ОБЩИЙ ЧАТ
# ==========================
@dp.message(F.chat.type.in_(["group", "supergroup"]))
async def group_chat_handler(message: types.Message):
    if not message.text: 
        await db.save_context(message.chat.id, message.from_user.id, "[Не текст]")
        return

    await db.save_user(message.from_user.id, message.from_user.username)
    await db.save_context(message.chat.id, message.from_user.id, message.text)
    context = await db.get_context(message.chat.id)
    
    bot_mentioned = f"@{BOT_USERNAME.lower()}" in message.text.lower()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.id
    
    current_time = time.time()
    last_time = chat_cooldowns.get(message.chat.id, 0)
    random_chance = False
    
    if current_time - last_time > 60:
        random_chance = random.random() < 0.05 
        
    if bot_mentioned or is_reply_to_bot or random_chance:
        chat_cooldowns[message.chat.id] = current_time
        user_data = await db.get_user(message.from_user.id)
        nickname = user_data["nickname"] if user_data and user_data["nickname"] else message.from_user.first_name
        
        prompt = f"Парень по кличке {nickname} пишет: '{message.text}'. Ответь ему коротко, как друг."
        response = await ai.ask_ai(prompt, context)
        await message.reply(response)

# ==========================
# [PHOTO] ФОТО (ВРЕМЕННО ОТКЛЮЧЕНО)
# ==========================
# Анализ фото требует системных библиотек, которых нет на Render.
# Включим позже, когда бот будет стабильно работать.

# ==========================
# [LOCATION] ГЕОЛОКАЦИИ
# ==========================
@dp.message(F.location)
async def location_handler(message: types.Message):
    lat = message.location.latitude    lon = message.location.longitude
    await db.save_place(f"Точка от {message.from_user.first_name}", lat, lon, "покатушки")
    await message.reply("Засёк координаты 📍 Сохранил в базу! Теперь все могут найти это место командой /places в личке.")
    
    try:
        await bot.send_message(message.from_user.id, f"Слыш, ты скинул точку в чат. Как это место называется? Что там за атмосфера?")
    except:
        pass 

# ==========================
# [CHANNEL] КАНАЛ
# ==========================
@dp.message(Command("post"), F.chat.type == "private")
async def generate_post(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Кидай черновик или тему, я сделаю огонь-пост для канала! 🔥")
    user_states[message.from_user.id] = {"step": "wait_post"}

@dp.message(F.chat.type == "private", lambda m: user_states.get(m.from_user.id, {}).get("step") == "wait_post")
async def process_post(message: types.Message):
    prompt = f"Сделай из этого черновика живой пост для Telegram-канала мотосообщества 'Альфаводы'. Добавь сленга и эмоций. Черновик: {message.text}"
    post_text = await ai.ask_ai(prompt)
    await message.answer(f"Вот готовый пост:\n\n{post_text}\n\nОтправить в канал? (Напиши 'Да')")
    user_states[message.from_user.id] = {"step": "confirm_post", "text": post_text}

@dp.message(F.chat.type == "private", lambda m: user_states.get(m.from_user.id, {}).get("step") == "confirm_post")
async def confirm_post(message: types.Message):
    if message.text.lower() in ["да", "д", "yes"]:
        try:
            await bot.send_message(CHANNEL_ID, user_states[message.from_user.id]["text"])
            await message.answer("Улетело в канал! 🚀")
        except Exception as e:
            await message.answer(f"Ошибка: {e}. Убедись, что я админ в канале.")
    if message.from_user.id in user_states: del user_states[message.from_user.id]

@dp.message(Command("idea"), F.chat.type == "private")
async def generate_idea(message: types.Message):
    context = await db.get_context(message.chat.id)
    prompt = f"Посмотри на вайб чата: {context}. Предложи 3 дерзкие идеи для поста в канал. Без воды."
    ideas = await ai.ask_ai(prompt)
    await message.answer(f"Вот идеи, выбирай:\n\n{ideas}")

# ==========================
# [START] ЗАПУСК
# ==========================
async def main():
    web_runner = await start_web_server()
    
    try:
        await dp.start_polling(bot)    finally:
        await web_runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
