import os
import sys
import logging
import requests
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
​
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
​
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
​
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    logger.error("Missing TELEGRAM_TOKEN or GEMINI_API_KEY")
    sys.exit(1)
​
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
​
user_images = {}
​
WELCOME = """سلام! ربات تحلیل تصویر آماده‌ست
​
یک تصویر بفرست تا شروع کنیم!"""
​
ACTIONS = [
    [("توضیح فارسی", "fa"), ("Describe English", "en")],
    [("کپشن اینستا", "insta"), ("متن تبلیغاتی", "ad")],
    [("راهنمای ویرایش", "edit"), ("متن SEO", "seo")],
]
​
PROMPTS = {
    "fa": "این تصویر رو به فارسی کامل توضیح بده.",
    "en": "Describe this image in detail in English.",
    "insta": "سه کپشن اینستاگرامی جذاب فارسی با هشتگ بنویس.",
    "ad": "یک متن تبلیغاتی حرفه‌ای فارسی بنویس.",
    "edit": "پیشنهادهای حرفه‌ای برای بهبود این تصویر بده.",
    "seo": "Alt tag و توضیح SEO فارسی برای این تصویر بنویس.",
}
​
def ask_gemini(image_bytes, prompt):
    img_b64 = base64.b64encode(image_bytes).decode()
    body = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]
        }]
    }
    r = requests.post(GEMINI_URL, json=body, timeout=40)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
​
def make_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t, callback_data=cb) for t, cb in row] for row in ACTIONS]
    )
​
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME)
​
async def photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    r = requests.get(file.file_path)
    user_images[uid] = r.content
    await update.message.reply_text(
        "تصویر دریافت شد! یکی رو انتخاب کن:",
        reply_markup=make_keyboard()
    )
​
async def button_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in user_images:
        await q.message.reply_text("ابتدا یک تصویر بفرست!")
        return
    prompt = PROMPTS.get(q.data, "")
    await run_analysis(q.message, uid, prompt)
​
async def text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_images:
        await update.message.reply_text("ابتدا یک تصویر بفرست!")
        return
    await run_analysis(update.message, uid, update.message.text)
​
async def run_analysis(message, uid, prompt):
    msg = await message.reply_text("در حال تحلیل...")
    try:
        result = ask_gemini(user_images[uid], prompt)
        await msg.edit_text(result)
    except Exception as e:
        await msg.edit_text(f"خطا: {e}")
​
if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_received))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_received))
    app.add_handler(CallbackQueryHandler(button_pressed))
    logger.info("Bot started!")
    app.run_polling()
​
