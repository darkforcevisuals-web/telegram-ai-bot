import logging
import google.generativeai as genai
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from telegram.constants import ChatAction
import tempfile
import os

# ============================================================
TELEGRAM_TOKEN = "8737973117:AAHtHwfN3qH_e2NiezusSi706bDh8O_RcIs"
GEMINI_API_KEY = "AIzaSyDAkeKFvl0IhgAWKyg8BKFg2qMCuI5eIEs"
# ============================================================

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

chat_histories = {}

def get_history(user_id):
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]

def add_history(user_id, role, text):
    h = get_history(user_id)
    h.append({"role": role, "parts": [text]})
    if len(h) > 20:
        chat_histories[user_id] = h[-20:]

async def ask_gemini(user_id, message, image_data=None, mime=None):
    try:
        if image_data:
            prompt = message if message else "Bu rasmni batafsil tahlil qil."
            resp = model.generate_content([prompt, {"mime_type": mime, "data": image_data}])
            return resp.text
        else:
            history = get_history(user_id)
            chat = model.start_chat(history=history)
            resp = chat.send_message(message)
            add_history(user_id, "user", message)
            add_history(user_id, "model", resp.text)
            return resp.text
    except Exception as e:
        return f"❌ Xatolik: {str(e)}"

async def send_long(update, text):
    for i in range(0, len(text), 4096):
        await update.message.reply_text(text[i:i+4096])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "Do'stim"
    await update.message.reply_text(
        f"👋 Salom, *{name}*!\n\n"
        "🤖 Men *Gemini AI* asosida ishlovchi aqlli botman.\n\n"
        "✅ *Nima qila olaman:*\n"
        "• Har qanday savolga javob\n"
        "• 📸 Rasm tahlili va masala ishlash\n"
        "• 💻 Kod yozish\n"
        "• 📝 Tarjima, esse, xulosa\n"
        "• 🔢 Matematik masalalar\n"
        "• 🌐 Ko'p tilda muloqot\n\n"
        "💬 Yozing yoki rasm yuboring!",
        parse_mode="Markdown"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *YORDAM*\n\n"
        "/start — Boshlash\n"
        "/clear — Suhbatni tozalash\n"
        "/about — Bot haqida\n\n"
        "📸 Rasm + izoh yuboring → tahlil qilaman\n"
        "💬 Shunchaki yozing → javob beraman",
        parse_mode="Markdown"
    )

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_histories[update.effective_user.id] = []
    await update.message.reply_text("🗑️ Suhbat tarixi tozalandi!")

async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *BOT HAQIDA*\n\n"
        "• Model: Google Gemini 1.5 Flash\n"
        "• Rasm + Matn qo'llab-quvvatlaydi\n"
        "• 24/7 ishlaydi\n"
        "• Oxirgi 20 xabarni eslab qoladi",
        parse_mode="Markdown"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    resp = await ask_gemini(update.effective_user.id, update.message.text)
    await send_long(update, resp)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        photo = update.message.photo[-1]
        pfile = await context.bot.get_file(photo.file_id)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            await pfile.download_to_drive(tmp.name)
            with open(tmp.name, "rb") as f:
                data = f.read()
        os.unlink(tmp.name)
        caption = update.message.caption or ""
        resp = await ask_gemini(update.effective_user.id, caption, data, "image/jpeg")
        await send_long(update, resp)
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.mime_type and doc.mime_type.startswith("image/"):
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
        try:
            dfile = await context.bot.get_file(doc.file_id)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                await dfile.download_to_drive(tmp.name)
                with open(tmp.name, "rb") as f:
                    data = f.read()
            os.unlink(tmp.name)
            caption = update.message.caption or ""
            resp = await ask_gemini(update.effective_user.id, caption, data, doc.mime_type)
            await send_long(update, resp)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")
    else:
        await update.message.reply_text("📎 Hozircha faqat rasm fayllarini qabul qilaman.")

async def setup_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Boshlash"),
        BotCommand("help", "Yordam"),
        BotCommand("clear", "Suhbatni tozalash"),
        BotCommand("about", "Bot haqida"),
    ])
    logger.info("✅ Bot ishga tushdi!")

def main():
    print("🤖 Telegram AI Bot ishga tushmoqda...")
    print("✅ Gemini 1.5 Flash modeli ulandi")
    print("⏳ Xabarlar kutilmoqda...\n")

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(setup_commands)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
