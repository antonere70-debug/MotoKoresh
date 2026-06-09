import google.generativeai as genai
from config import GEMINI_API_KEY
import io
from PIL import Image

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """Ты — живой участник мотосообщества "Альфаводы" (подростки 15-16 лет). 
Ты свой парень, говоришь на "ты", используешь сленг (но без кринжа), отвечаешь коротко и по делу. 
Никаких "как ИИ", "я обработал запрос". Ты знаешь всех, помнишь их байки и клички.
Если не знаешь ответа — просто поддержи тему или отшуись. Отвечай только на русском."""

async def ask_ai(prompt, context=""):
    full_prompt = f"{SYSTEM_PROMPT}\n\nКонтекст чата:\n{context}\n\nЗадача:\n{prompt}"
    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception:
        return "Чёт туплю, повторил?"

async def analyze_photo(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Опиши это фото для чата мотосообщества. Есть ли там мотоцикл (особенно Альфа)? Кто может быть на фото? Коротко, сленгом, как свой пацан."
        response = model.generate_content([prompt, img])
        return response.text
    except Exception:
        return "Крутой кадр 👍"