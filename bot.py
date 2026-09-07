import os
import sys
import logging
import requests
import io
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
​
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
​
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
​
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN is missing!")
    sys.exit(1)
​
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is missing!")
    sys.exit(1)
​
logger.info(f"Gemini key loaded: {GEMINI_API_KEY[:8]}...")
​
# Use Gemini REST API directly (no SDK auth issues)
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
​
user_sessions = {}
​
WELCOME_TEXT = """✍️ سلام! من ربات تحلیل و ویرایش تصویر هستم ⚡
​
📸 یک تصویر برام بفرست و بعد بگو چیکار میخوای:
​
• 🔍 توضیح تصویر (فارسی و انگلیسی)
• 📝 تولید کپشن اینستاگرام
• 📢 متن تبلیغاتی حرفه‌ای
• 🔎 راهنمای ویرایش حرفه‌ای
• ❓ هر سوالی درباره تصویر"""
​
QUICK_ACTIONS = [
    [("\U0001f50d توضیح فارسی", "describe_fa"), ("\U0001f310 Describe English", "describe_en")],
    [("\U0001f4dd کپشن اینستا", "caption_insta"), ("\U0001f4e2 متن تبلیغاتی", "ad_text")],
    [("\U0001f50e راهنمای ویرایش", "edit_guide"), ("\U0001f4dc متن SEO", "seo_alt")],
]
​
PROMPTS = {
    "describe_fa": "تصویر رو به فارسی دقیق و کامل توضیح بده. همه جزئیات رو بگو.",
    "describe_en": "Describe this image in detail in English. Cover all elements, colors, composition, mood and context.",
    "caption_insta": "برای این تصویر ۳ کپشن جذاب اینستاگرامی بنویس (فارسی). هر کدام با هشتگ و ایموجی مناسب باشه.",
    "ad_text": "برای این تصویر یک متن تبلیغاتی جذاب بنویس. شامل هدلاین، بدنه متن و کال تو اکشن.",
    "edit_guide": "به عنوان متخصص طراحی گرافیک، پیشنهادهای دقیق برای بهبود این تصویر بده.",
    "seo_alt": "برای این تصویر بنویس: ۱) تگ Alt سئوی ۲) عنوان صفحه ۳) توضیح تصویر برای وبسایت.",
}
​
def call_gemini(prompt: str, image_bytes: bytes) -> str:
    import base64
    image_b64 = base64.b64encode(image_bytes).decode()
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
            ]
        }]
    }
    
    resp = requests.post(GEMINI_API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]
​
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)
​
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    response = requests.get(file.file_path)
    image_bytes = response.content
    user_sessions[user_id] = {"image_bytes": image_bytes}
    
    keyboard = [[InlineKeyboardButton(text, callback_data=cb) for text, cb in row] for row in QUICK_ACTIONS]
    await update.message.reply_text(
        "✅ تصویر دریافت شد! یکی رو انتخاب کن یا هر سوالی داری بنویس ❤️",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
​
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in user_sessions:
        await query.message.reply_text("⚠️ ابتدا یک تصویر بفرست!")
        return
    prompt = PROMPTS.get(query.data, "")
    await process_image(query.message, user_id, prompt)
​
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("📸 ابتدا یک تصویر بفرست!")
        return
    await process_image(update.message, user_id, update.message.text)
​
async def process_image(message, user_id: int, prompt: str):
    thinking = await message.reply_text("⏳ در حال تحلیل...")
    try:
        image_bytes = user_sessions[user_id]["image_bytes"]
        result = call_gemini(prompt, image_bytes)
        await thinking.delete()
        keyboard = [[InlineKeyboardButton(text, callback_data=cb) for text, cb in row] for row in QUICK_ACTIONS]
        await message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await thinking.edit_text(f"❌ خطا: {str(e)}")
​
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Bot is running!")
    app.run_polling()
​
if __name__ == "__main__":
    main()
