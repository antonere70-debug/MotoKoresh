import google.generativeai as genai
from config import GEMINI_API_KEY

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
