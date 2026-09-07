import os, sys, logging, requests, base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
KEY = os.environ["GEMINI_API_KEY"].strip()

MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest"]
BASE = "https://generativelanguage.googleapis.com/v1beta/models/"

imgs = {}
KB = [[("توضیح فارسی","fa"),("English","en")],[("کپشن اینستا","insta"),("متن تبلیغ","ad")]]
PR = {"fa":"این تصویر رو به فارسی کامل توضیح بده.","en":"Describe this image in detail in English.","insta":"سه کپشن اینستاگرامی فارسی با هشتگ بنویس.","ad":"متن تبلیغاتی حرفهای فارسی بنویس."}

def mk(): return InlineKeyboardMarkup([[InlineKeyboardButton(t,callback_data=c) for t,c in r] for r in KB])

def ask(img, prompt):
    b64 = base64.b64encode(img).decode()
    body = {"contents":[{"parts":[{"text":prompt},{"inline_data":{"mime_type":"image/jpeg","data":b64}}]}]}
    for model in MODELS:
        url = BASE + model + ":generateContent?key=" + KEY
        try:
            r = requests.post(url, json=body, timeout=40)
            if r.status_code == 200:
                logger.info(f"Working model: {model}")
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            logger.warning(f"Model {model}: {r.status_code} - {r.text[:150]}")
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
    raise Exception("هیچ مدلی در دسترس نیست.")

async def start(u,c): await u.message.reply_text("سلام! یک تصویر بفرست.")
async def photo(u,c):
    uid=u.effective_user.id
    f=await c.bot.get_file(u.message.photo[-1].file_id)
    imgs[uid]=requests.get(f.file_path).content
    await u.message.reply_text("تصویر دریافت شد! انتخاب کن:",reply_markup=mk())
async def btn(u,c):
    q=u.callback_query; await q.answer(); uid=q.from_user.id
    if uid not in imgs: await q.message.reply_text("اول تصویر بفرست!"); return
    m=await q.message.reply_text("در حال تحلیل...")
    try: await m.edit_text(ask(imgs[uid],PR.get(q.data,"")))
    except Exception as e: await m.edit_text(f"خطا: {e}")
async def txt(u,c):
    uid=u.effective_user.id
    if uid not in imgs: await u.message.reply_text("اول تصویر بفرست!"); return
    m=await u.message.reply_text("در حال تحلیل...")
    try: await m.edit_text(ask(imgs[uid],u.message.text))
    except Exception as e: await m.edit_text(f"خطا: {e}")

app=Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start",start))
app.add_handler(MessageHandler(filters.PHOTO,photo))
app.add_handler(MessageHandler(filters.TEXT&~filters.COMMAND,txt))
app.add_handler(CallbackQueryHandler(btn))
logger.info("Bot started!")
app.run_polling()
