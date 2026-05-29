import os
import logging
import google.generativeai as genai
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from telegram.constants import ChatAction
import tempfile

# ============================================================
#  SOZLAMALAR
# ============================================================
TELEGRAM_TOKEN = "8737973117:AAHtHwfN3qH_e2NiezusSi706bDh8O_RcIs"
GEMINI_API_KEY = "AIzaSyDAkeKFvl0IhgAWKyg8BKFg2qMCuI5eIEs"

# Gemini sozlash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Har bir foydalanuvchining suhbat tarixi
chat_histories = {}

# ============================================================
#  YORDAMCHI FUNKSIYALAR
# ============================================================

def get_chat_history(user_id: int):
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]

def add_to_history(user_id: int, role: str, text: str):
    history = get_chat_history(user_id)
    history.append({"role": role, "parts": [text]})
    # Oxirgi 20 ta xabarni saqlash (xotira uchun)
    if len(history) > 20:
        chat_histories[user_id] = history[-20:]

async def ask_gemini(user_id: int, user_message: str, image_data=None, image_mime=None) -> str:
    try:
        if image_data:
            # Rasm bilan so'rov
            image_part = {"mime_type": image_mime, "data": image_data}
            prompt = user_message if user_message else "Bu rasmni tahlil qil va batafsil tushuntir."
            response = model.generate_content([prompt, image_part])
            return response.text
        else:
            # Matnli suhbat (tarix bilan)
            history = get_chat_history(user_id)
            chat = model.start_chat(history=history)
            response = chat.send_message(user_message)
            add_to_history(user_id, "user", user_message)
            add_to_history(user_id, "model", response.text)
            return response.text
    except Exception as e:
        logger.error(f"Gemini xatosi: {e}")
        return f"❌ Xatolik yuz berdi: {str(e)}"

# ============================================================
#  BUYRUQLAR
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Do'stim"
    text = (
        f"👋 Salom, *{name}*!\n\n"
        "Men *Gemini AI* asosida ishlovchi aqlli botman.\n\n"
        "🧠 *Nima qila olaman:*\n"
        "• Har qanday savolga javob beraman\n"
        "• 📸 Rasm yuborang → tahlil qilaman / masala ishlayman\n"
        "• 💻 Kod yozaman va tushuntiraman\n"
        "• 📝 Esse, tarjima, xulosa yozaman\n"
        "• 🔢 Matematik masalalar\n"
        "• 🌐 Ko'p tilda gaplashaman\n\n"
        "📌 *Buyruqlar:*\n"
        "/start — Boshlash\n"
        "/help — Yordam\n"
        "/clear — Suhbatni tozalash\n"
        "/about — Bot haqida\n\n"
        "💬 Shunchaki yozing yoki rasm yuboring!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *YORDAM*\n\n"
        "🔹 *Oddiy savol:* Shunchaki yozing\n"
        "🔹 *Rasm tahlili:* Rasm yuboring (izohlash bilan yoki izohlashsiz)\n"
        "🔹 *Masala:* Rasm yuboring + 'bu masalani ishla'\n"
        "🔹 *Kod:* 'Python da... yoz' deb so'rang\n"
        "🔹 *Tarjima:* '...ni inglizchaga tarjima qil'\n\n"
        "📌 *Buyruqlar:*\n"
        "/clear — Suhbat tarixini o'chirish\n"
        "/about — Bot haqida ma'lumot\n\n"
        "⚡ Men suhbat tarixini eslab qolaman (oxirgi 20 xabar)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_histories[user_id] = []
    await update.message.reply_text(
        "🗑️ Suhbat tarixi tozalandi! Yangi suhbat boshlashingiz mumkin.",
        parse_mode="Markdown"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *BOT HAQIDA*\n\n"
        "• *Model:* Google Gemini 1.5 Flash\n"
        "• *Qobiliyat:* Matn + Rasm (Multimodal)\n"
        "• *Til:* O'zbek, Rus, Ingliz va boshqalar\n"
        "• *Ishlash rejimi:* 24/7\n"
        "• *Xotira:* Oxirgi 20 xabarni eslab qoladi\n\n"
        "✅ *ChatGPT va Gemini kabi AI imkoniyatlari*"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ============================================================
#  MATN XABARLARI
# ============================================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Yozmoqda... ko'rsatish
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    response = await ask_gemini(user_id, user_message)

    # Javob 4096 belgidan uzun bo'lsa, bo'lib yuborish
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            await update.message.reply_text(response[i:i+4096])
    else:
        await update.message.reply_text(response)

# ============================================================
#  RASM XABARLARI
# ============================================================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    caption = update.message.caption or ""

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    try:
        # Eng katta rasmni olish
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)

        # Rasmni yuklab olish
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            await photo_file.download_to_drive(tmp.name)
            with open(tmp.name, "rb") as f:
                image_data = f.read()

        # Gemini ga yuborish
        response = await ask_gemini(
            user_id,
            caption if caption else "Bu rasmni batafsil tahlil qil. Agar masala yoki matn bo'lsa, hal qil.",
            image_data=image_data,
            image_mime="image/jpeg"
        )

        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                await update.message.reply_text(response[i:i+4096])
        else:
            await update.message.reply_text(response)

        # Vaqtinchalik faylni o'chirish
        os.unlink(tmp.name)

    except Exception as e:
        logger.error(f"Rasm xatosi: {e}")
        await update.message.reply_text(f"❌ Rasmni qayta ishlashda xatolik: {str(e)}")

# ============================================================
#  DOKUMENT (PDF, fayl) XABARLARI
# ============================================================

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document
    caption = update.message.caption or ""

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    # Rasm fayllari uchun
    if doc.mime_type and doc.mime_type.startswith("image/"):
        try:
            doc_file = await context.bot.get_file(doc.file_id)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                await doc_file.download_to_drive(tmp.name)
                with open(tmp.name, "rb") as f:
                    image_data = f.read()

            response = await ask_gemini(
                user_id,
                caption if caption else "Bu rasmni batafsil tahlil qil.",
                image_data=image_data,
                image_mime=doc.mime_type
            )
            await update.message.reply_text(response)
            os.unlink(tmp.name)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")
    else:
        await update.message.reply_text(
            "📎 Hozircha faqat rasm fayllarini qayta ishlay olaman.\n"
            "Matn yoki PDF uchun tez orada yangilanish bo'ladi!"
        )

# ============================================================
#  OVOZLI XABAR
# ============================================================

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎤 Ovozli xabarni eshitdim, lekin hozircha ovozni matnга aylantirish funksiyasi qo'shilmagan.\n"
        "Iltimos, yozma xabar yuboring!"
    )

# ============================================================
#  NOMA'LUM XABAR TURLARI
# ============================================================

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😄 Zo'r sticker! Lekin men matn va rasmlarga javob beraman.")

# ============================================================
#  ASOSIY FUNKSIYA
# ============================================================

async def post_init(application: Application):
    """Bot buyruqlarini o'rnatish"""
    commands = [
        BotCommand("start", "Botni boshlash"),
        BotCommand("help", "Yordam"),
        BotCommand("clear", "Suhbatni tozalash"),
        BotCommand("about", "Bot haqida"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")

def main():
    print("🤖 Telegram AI Bot ishga tushmoqda...")
    print("✅ Gemini 1.5 Flash modeli ulandi")
    print("⏳ Xabarlar kutilmoqda...\n")

    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Buyruq handlerlari
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("about", about_command))

    # Xabar handlerlari
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

    # Botni ishga tushirish
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
