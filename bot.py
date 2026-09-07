import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from PIL import Image
import io
import requests

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Config from environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Store user sessions: {user_id: {"image_bytes": ..., "history": [...]}}
user_sessions = {}

WELCOME_TEXT = """✍️ سلام! من ربات تحلیل و ویرایش تصویر هستم ⚡

📸 یک تصویر برام بفرست و بعد بگو چیکار میخوای:

• 🔍 توضیح تصویر
• 🎨 ویرایش هوشمند
• 📝 تولید کپشن و متن تبلیغاتی
• 🌐 ترجمه توضیح تصویر
• ❓ هر سوالی درباره تصویر
برای شروع /start بزن"""

QUICK_ACTIONS = [
    [("\U0001f50d توضیح فارسی", "describe_fa"), ("\U0001f310 Describe English", "describe_en")],
    [("\U0001f4dd کپشن اینستا", "caption_insta"), ("\U0001f4e2 متن تبلیغاتی", "ad_text")],
    [("\U0001f50e راهنمای ویرایش", "edit_guide"), ("\U0001f4dc متن وبسایت", "seo_alt")],
]

PROMPTS = {
    "describe_fa": "تصویر رو به فارسی دقیق و کامل توضیح بده. همه جزئیات رو بگو.",
    "describe_en": "Describe this image in detail in English. Cover all elements, colors, composition, mood and context.",
    "caption_insta": "برای این تصویر ۳ کپشن جذاب اینستاگرامی بنویس (فارسی). هر کدام با هشتگ و ایموجی مناسب باشه.",
    "ad_text": "برای این تصویر یک متن تبلیغاتی جذاب و حرفه‌ای بنویس. شامل هدلاین، بدنه متن و کال تو اکشن باشه.",
    "edit_guide": "به عنوان یک متخصص طراحی گرافیک، پیشنهادهای دقیق برای بهبود این تصویر بده (رنگ، نورپردازی، ترکیب‌بندی، فونت و ...).",
    "seo_alt": "برای این تصویر بنویس: ۱) تگ Alt سئوی جامع ۲) عنوان صفحه ۳) توضیح تصویر برای وبسایت.",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]  # highest resolution
    file = await context.bot.get_file(photo.file_id)
    
    # Download image
    response = requests.get(file.file_path)
    image_bytes = response.content
    
    # Store in session
    user_sessions[user_id] = {
        "image_bytes": image_bytes,
        "history": []
    }
    
    # Build inline keyboard
    keyboard = [[InlineKeyboardButton(text, callback_data=cb) for text, cb in row] for row in QUICK_ACTIONS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ تصویر دریافت شد! یکی رو انتخاب کن یا هر سوالی داری بنویس ❤️",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id not in user_sessions or "image_bytes" not in user_sessions[user_id]:
        await query.message.reply_text("⚠️ ابتدا یک تصویر بفرست!")
        return
    
    prompt = PROMPTS.get(query.data, "")
    await process_image_with_prompt(query.message, user_id, prompt)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    if user_id not in user_sessions or "image_bytes" not in user_sessions[user_id]:
        await update.message.reply_text(
            "📸 ابتدا یک تصویر برام بفرست و بعد سوالت رو بنویس 😊"
        )
        return
    
    await process_image_with_prompt(update.message, user_id, user_text)

async def process_image_with_prompt(message, user_id: int, prompt: str):
    thinking_msg = await message.reply_text("⏳ در حال تحلیل...")
    
    try:
        session = user_sessions[user_id]
        image_bytes = session["image_bytes"]
        
        # Convert to PIL Image for Gemini
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        response = model.generate_content([prompt, pil_image])
        result_text = response.text
        
        # Save to history
        session["history"].append({"q": prompt, "a": result_text})
        
        await thinking_msg.delete()
        
        # Add keyboard again for follow-up
        keyboard = [[InlineKeyboardButton(text, callback_data=cb) for text, cb in row] for row in QUICK_ACTIONS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            result_text,
            reply_markup=reply_markup
        )
    except Exception as e:
        await thinking_msg.edit_text(f"❌ خطای رخ داد: {str(e)}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
