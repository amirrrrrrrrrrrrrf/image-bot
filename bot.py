import os, logging, requests, base64, io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_TOKEN"].strip()
KEY = os.environ["GEMINI_API_KEY"].strip()
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=" + KEY

NO_FORMAT = (
    "مهم: هرگز از markdown، bold، italic، هدینگ یا هیچ قالب‌بندی خاصی استفاده نکن. "
    "هیچ ستاره (**)، آندرلاین (_)، هشتگ (#) یا بک‌تیک (`) در متن نزن. "
    "فقط متن ساده بنویس. پاسخ‌ها کوتاه و طبیعی باشن مگر ضرورت داشته باشه."
)

SYSTEM_PROMPTS = {
    "therapist": f"تو یک دوست صمیمی و دلسوز هستی که کمک می‌کنی. با احترام و مهربانی گوش بده و کمک کن. {NO_FORMAT}",
    "idea":      f"تو یک ایده‌پرداز خلاق هستی. ایده‌های جذاب و کاربردی بده. {NO_FORMAT}",
    "caption":   f"تو متخصص کپشن‌نویسی برای اینستاگرام هستی. کپشن‌های جذاب و مناسب بنویس. {NO_FORMAT}",
    "calendar":  f"تو متخصص تقویم محتوایی هستی. تقویم منظم و کاربردی بساز. {NO_FORMAT}",
    "bio":       f"تو متخصص بیو‌نویسی هستی. بیوهای جذاب و حرفه‌ای بنویس. {NO_FORMAT}",
    "hashtag":   f"تو متخصص هشتگ‌گذاری هستی. هشتگ‌های مرتبط و موثر پیشنهاد بده. {NO_FORMAT}",
    "edit":      f"تو ویراستار متن هستی. متن را بهتر، روان‌تر و زیباتر کن. {NO_FORMAT}",
    "script":    f"تو نویسنده اسکریپت ریلز و استوری هستی. اسکریپت جذاب بنویس. {NO_FORMAT}",
    "translate": f"تو مترجم حرفه‌ای هستی. متن را دقیق و روان ترجمه کن. {NO_FORMAT}",
    "summarize": f"تو خلاصه‌ساز هستی. متن را کوتاه و جامع خلاصه کن. {NO_FORMAT}",
}

MODE_INTROS = {
    "therapist": "اینجام و گوش می‌دم. هر چیزی که داری بگو.",
    "idea":      "موضوعت رو بگو تا ایده‌های خلاقانه بهت بدم.",
    "caption":   "عکس یا ویدیو بفرست تا کپشن بنویسم.",
    "calendar":  "بگو در چه حوزه‌ای فعالیت می‌کنی تا تقویم بسازم.",
    "bio":       "اطلاعاتی درباره خودت یا کارت بگو تا بیو بنویسم.",
    "hashtag":   "موضوع یا متنت رو بنویس یا عکس بفرست.",
    "edit":      "متنی که می‌خوای ویرایش بشه رو بفرست.",
    "script":    "موضوع ریلز یا استوریت رو بگو.",
    "translate": "متنی که می‌خوای ترجمه بشه رو بفرست.",
    "summarize": "متنی که می‌خوای خلاصه بشه رو بفرست.",
}

states = {}

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 تراپیست",         callback_data="mode_therapist"),
         InlineKeyboardButton("💡 ایده‌پرداز",       callback_data="mode_idea")],
        [InlineKeyboardButton("📝 کپشن‌ساز",        callback_data="mode_caption"),
         InlineKeyboardButton("📅 تقویم محتوا",    callback_data="mode_calendar")],
        [InlineKeyboardButton("✨ بیو‌نویس",        callback_data="mode_bio"),
         InlineKeyboardButton("# هشتگ‌ساز",        callback_data="mode_hashtag")],
        [InlineKeyboardButton("✂️ ویرایش متن",     callback_data="mode_edit"),
         InlineKeyboardButton("🎬 اسکریپت",         callback_data="mode_script")],
        [InlineKeyboardButton("🌐 مترجم",           callback_data="mode_translate"),
         InlineKeyboardButton("📄 خلاصه‌ساز",      callback_data="mode_summarize")],
    ])

def caption_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 تصویر",  callback_data="cap_image"),
         InlineKeyboardButton("🎬 ویدیو", callback_data="cap_video")],
        [InlineKeyboardButton("🏠 منو",    callback_data="main_menu")],
    ])

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منو", callback_data="main_menu")]])

def get_state(uid):
    return states.get(uid, {"mode": None, "step": None, "data": {}})

def set_state(uid, mode, step, data=None):
    states[uid] = {"mode": mode, "step": step, "data": data or {}}

def clear_state(uid):
    states.pop(uid, None)

def ask_gemini(prompt, image_bytes=None):
    parts = [{"text": prompt}]
    if image_bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            parts.append({"inline_data": {"mime_type": "image/jpeg",
                                          "data": base64.b64encode(buf.getvalue()).decode()}})
        except:
            pass
    r = requests.post(GEMINI_URL, json={"contents": [{"parts": parts}]}, timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

WELCOME = (
    "سلام! خوش اومدی 👋\n\n"
    "من دستیار محتوای توام. از منوی زیر یه حالت انتخاب کن تا شروع کنیم:"
)

async def start(u, c):
    uid = u.effective_user.id
    clear_state(uid)
    await u.message.reply_text(WELCOME, reply_markup=main_kb())

async def handle_callback(u, c):
    q = u.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data == "main_menu":
        clear_state(uid)
        await q.message.reply_text("منوی اصلی:", reply_markup=main_kb())
        return

    if data.startswith("mode_"):
        mode = data[5:]
        if mode == "caption":
            set_state(uid, "caption", "choose_media")
            await q.message.reply_text("برای کپشن، نوع مدیا را انتخاب کن:", reply_markup=caption_kb())
        else:
            set_state(uid, mode, "talking")
            await q.message.reply_text(MODE_INTROS[mode], reply_markup=back_kb())
        return

    if data == "cap_image":
        s = get_state(uid)
        s["data"]["media_type"] = "image"
        set_state(uid, "caption", "waiting_media", s["data"])
        await q.message.reply_text("عکست رو بفرست.", reply_markup=back_kb())
        return

    if data == "cap_video":
        s = get_state(uid)
        s["data"]["media_type"] = "video"
        set_state(uid, "caption", "waiting_media", s["data"])
        await q.message.reply_text("ویدیوت رو بفرست.", reply_markup=back_kb())
        return

async def handle_photo(u, c):
    uid = u.effective_user.id
    s = get_state(uid)
    photo = u.message.photo[-1]
    file = await c.bot.get_file(photo.file_id)
    img_bytes = requests.get(file.file_path).content

    if s["mode"] == "caption" and s["step"] == "waiting_media":
        s["data"]["image"] = img_bytes
        set_state(uid, "caption", "ask_style", s["data"])
        await u.message.reply_text("سبک کپشن رو بگو (مثلا: طنز، انگیزشی، فروش، معرفی)", reply_markup=back_kb())
        return

    if s["mode"] == "hashtag":
        msg = await u.message.reply_text("در حال ساخت هشتگ...")
        try:
            result = ask_gemini(SYSTEM_PROMPTS["hashtag"] + "\n\nبرای این تصویر هشتگ مناسب بساز.", img_bytes)
            await msg.edit_text(result, reply_markup=back_kb())
        except Exception as e:
            await msg.edit_text(f"خطا: {e}", reply_markup=back_kb())
        return

    await u.message.reply_text("ابتدا یک گزینه از منو انتخاب کن:", reply_markup=main_kb())

async def handle_video(u, c):
    uid = u.effective_user.id
    s = get_state(uid)

    if s["mode"] == "caption" and s["step"] == "waiting_media":
        msg = await u.message.reply_text("در حال بررسی ویدیو...")
        try:
            video = u.message.video or u.message.document
            file = await c.bot.get_file(video.file_id)
            video_bytes = requests.get(file.file_path).content
            b64 = base64.b64encode(video_bytes).decode()
            body = {"contents": [{"parts": [
                {"text": SYSTEM_PROMPTS["caption"] + "\n\nاین ویدیو را تحلیل کن و یک توضیح کوتاه بده."},
                {"inline_data": {"mime_type": "video/mp4", "data": b64}}
            ]}]}
            r = requests.post(GEMINI_URL, json=body, timeout=90)
            if r.status_code == 200:
                desc = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                s["data"]["video_desc"] = desc
                set_state(uid, "caption", "ask_style", s["data"])
                await msg.edit_text("ویدیو آنالیز شد. سبک کپشن رو بگو (طنز، انگیزشی، فروش، معرفی)", reply_markup=back_kb())
            else:
                set_state(uid, "caption", "ask_video_desc", s["data"])
                await msg.edit_text("ویدیو آنالیز نشد. لطفا خودت یک توضیح کوتاه از ویدیو بنویس.", reply_markup=back_kb())
        except Exception:
            set_state(uid, "caption", "ask_video_desc", s["data"])
            await msg.edit_text("ویدیو آنالیز نشد. لطفا خودت یک توضیح کوتاه از ویدیو بنویس.", reply_markup=back_kb())
        return

    await u.message.reply_text("ابتدا یک گزینه از منو انتخاب کن:", reply_markup=main_kb())

async def handle_text(u, c):
    uid = u.effective_user.id
    text = u.message.text
    s = get_state(uid)

    if not s["mode"]:
        await u.message.reply_text(
            "ابتدا یک گزینه از منو انتخاب کن:",
            reply_markup=main_kb()
        )
        return

    mode = s["mode"]
    step = s["step"]
    msg = await u.message.reply_text("در حال پردازش...")

    try:
        if mode == "therapist":
            result = ask_gemini(SYSTEM_PROMPTS["therapist"] + f"\n\nکاربر: {text}")
            await msg.edit_text(result, reply_markup=back_kb())

        elif mode == "idea":
            result = ask_gemini(SYSTEM_PROMPTS["idea"] + f"\n\nموضوع: {text}")
            await msg.edit_text(result, reply_markup=back_kb())

        elif mode == "caption":
            if step == "ask_style":
                data = s["data"]
                image = data.get("image")
                video_desc = data.get("video_desc", "")
                if image:
                    prompt = SYSTEM_PROMPTS["caption"] + f"\n\nسبک: {text}\nکپشن مناسب بنویس."
                    result = ask_gemini(prompt, image)
                else:
                    prompt = SYSTEM_PROMPTS["caption"] + f"\n\nتوضیح ویدیو: {video_desc}\nسبک: {text}\nکپشن مناسب بنویس."
                    result = ask_gemini(prompt)
                await msg.edit_text(result, reply_markup=back_kb())
            elif step == "ask_video_desc":
                s["data"]["video_desc"] = text
                set_state(uid, "caption", "ask_style", s["data"])
                await msg.edit_text("سبک کپشن رو بگو (طنز، انگیزشی، فروش، معرفی)", reply_markup=back_kb())
            else:
                await msg.edit_text("از منو یک گزینه کپشن انتخاب کن.", reply_markup=main_kb())

        elif mode == "calendar":
            result = ask_gemini(SYSTEM_PROMPTS["calendar"] + f"\n\nحوزه: {text}\nیک تقویم محتوایی ۳۰ روزه بساز.")
            await msg.edit_text(result, reply_markup=back_kb())

        elif mode == "bio":
            result = ask_gemini(SYSTEM_PROMPTS["bio"] + f"\n\nاطلاعات: {text}\nبیو حرفه‌ای بنویس.")
            await msg.edit_text(result, reply_markup=back_kb())

        elif mode == "hashtag":
            result = ask_gemini(SYSTEM_PROMPTS["hashtag"] + f"\n\nموضوع: {text}")
            await msg.edit_text(result, reply_markup=back_kb())

        elif mode == "edit":
            result = ask_gemini(SYSTEM_PROMPTS["edit"] + f"\n\nمتن:\n{text}")
            await msg.edit_text(result, reply_markup=back_kb())

        elif mode == "script":
            result = ask_gemini(SYSTEM_PROMPTS["script"] + f"\n\nموضوع: {text}")
            await msg.edit_text(result, reply_markup=back_kb())

        elif mode == "translate":
            result = ask_gemini(SYSTEM_PROMPTS["translate"] + f"\n\n{text}")
            await msg.edit_text(result, reply_markup=back_kb())

        elif mode == "summarize":
            result = ask_gemini(SYSTEM_PROMPTS["summarize"] + f"\n\nمتن:\n{text}")
            await msg.edit_text(result, reply_markup=back_kb())

        else:
            await msg.edit_text("از منو یک گزینه انتخاب کن:", reply_markup=main_kb())

    except Exception as e:
        await msg.edit_text(f"خطا: {e}", reply_markup=back_kb())

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
logger.info("Bot v4 started!")
app.run_polling()
