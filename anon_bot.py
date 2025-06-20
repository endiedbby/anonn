import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ( Application, ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters)
from threading import Thread

# Замените на ваш Telegram ID
ADMIN_ID = 5752325781

user_messages = {}
user_original_messages = {}
admin_to_user_messages = {}
user_replied_to_admin = {}

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Отправь сюда анонимное сообщение и дождись ответа.")

async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📩 Вызван forward_to_admin")
    user = update.effective_user
    msg = update.message
    is_reply_to_admin = False
    admin_msg_caption = ""

    if msg.reply_to_message:
        replied_msg = msg.reply_to_message
        # Проверяем, является ли сообщение ответом администратора
        if (replied_msg.text and "📬 Ответ администратора:" in replied_msg.text) or            (replied_msg.caption and "📬 Ответ администратора:" in replied_msg.caption):
            is_reply_to_admin = True
            if replied_msg.text:
                admin_text = replied_msg.text.replace("📬 Ответ администратора:", "")
                preview = admin_text[:50] + "..." if len(admin_text) > 50 else admin_text
                admin_msg_caption = f" (ответ на: \"{preview}\")"
            elif replied_msg.photo:
                admin_msg_caption = " (ответ на фото админа)"
            elif replied_msg.video:
                admin_msg_caption = " (ответ на видео админа)"
            elif replied_msg.sticker:
                admin_msg_caption = " (ответ на стикер админа)"
            elif replied_msg.voice:
                admin_msg_caption = " (ответ на голосовое сообщение админа)"
            elif replied_msg.video_note:
                admin_msg_caption = " (ответ на видеосообщение админа)"
            elif replied_msg.animation:
                admin_msg_caption = " (ответ на GIF админа)"

    caption = f"📩 Сообщение от @{user.username or 'без username'} (ID: {user.id}){admin_msg_caption}"
    sent = None
    reply_to_msg_id = None

    if not is_reply_to_admin:
        for msg_id, stored_user_id in user_messages.items():
            if stored_user_id == user.id:
                reply_to_msg_id = msg_id
                break

    if msg.text:
        sent = await context.bot.send_message(chat_id=ADMIN_ID, text=f"{caption}:{msg.text}", reply_to_message_id=reply_to_msg_id)
    elif msg.photo:
        sent = await context.bot.send_photo(chat_id=ADMIN_ID, photo=msg.photo[-1].file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
    elif msg.video:
        sent = await context.bot.send_video(chat_id=ADMIN_ID, video=msg.video.file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
    elif msg.sticker:
        sent = await context.bot.send_sticker(chat_id=ADMIN_ID, sticker=msg.sticker.file_id, reply_to_message_id=reply_to_msg_id)
        await context.bot.send_message(chat_id=ADMIN_ID, text=caption, reply_to_message_id=reply_to_msg_id)
    elif msg.voice:
        sent = await context.bot.send_voice(chat_id=ADMIN_ID, voice=msg.voice.file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
    elif msg.video_note:
        sent = await context.bot.send_video_note(chat_id=ADMIN_ID, video_note=msg.video_note.file_id, reply_to_message_id=reply_to_msg_id)
        await context.bot.send_message(chat_id=ADMIN_ID, text=caption, reply_to_message_id=reply_to_msg_id)
    elif msg.animation:
        sent = await context.bot.send_animation(chat_id=ADMIN_ID, animation=msg.animation.file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
    else:
        await msg.reply_text("❗️ Тип сообщения не поддерживается.")
        return

    if sent:
        user_messages[sent.message_id] = user.id
        user_original_messages[sent.message_id] = msg.message_id

    confirm = await msg.reply_text("✅ Сообщение отправлено анонимно!")
    await asyncio.sleep(5)
    await confirm.delete()

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        msg = await update.message.reply_text("❗️Ответьте на сообщение, чтобы отправить его пользователю.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    replied_msg_id = update.message.reply_to_message.message_id
    if replied_msg_id in user_messages:
        user_id = user_messages[replied_msg_id]
        original_msg_id = user_original_messages.get(replied_msg_id)

        if update.message.text:
            reply = await context.bot.send_message(chat_id=user_id, text=f"📬 Ответ администратора:{update.message.text}", reply_to_message_id=original_msg_id)
        elif update.message.sticker:
            reply = await context.bot.send_sticker(chat_id=user_id, sticker=update.message.sticker.file_id, reply_to_message_id=original_msg_id)
        elif update.message.voice:
            reply = await context.bot.send_voice(chat_id=user_id, voice=update.message.voice.file_id, reply_to_message_id=original_msg_id)
        elif update.message.video_note:
            reply = await context.bot.send_video_note(chat_id=user_id, video_note=update.message.video_note.file_id, reply_to_message_id=original_msg_id)
        elif update.message.photo:
            reply = await context.bot.send_photo(chat_id=user_id, photo=update.message.photo[-1].file_id, reply_to_message_id=original_msg_id)
        elif update.message.video:
            reply = await context.bot.send_video(chat_id=user_id, video=update.message.video.file_id, reply_to_message_id=original_msg_id)
        elif update.message.animation:
            reply = await context.bot.send_animation(chat_id=user_id, animation=update.message.animation.file_id, reply_to_message_id=original_msg_id)
        else:
            return

        admin_to_user_messages[user_id] = reply.message_id
        confirm = await update.message.reply_text("✅ Ответ отправлен пользователю.")
        await asyncio.sleep(5)
        await confirm.delete()
    else:
        msg = await update.message.reply_text("⚠️ Не удалось определить получателя.")
        await asyncio.sleep(5)
        await msg.delete()

# Запуск
TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = RENDER_URL + WEBHOOK_PATH

if not TOKEN or not RENDER_URL:
    raise RuntimeError("❗ Убедись, что BOT_TOKEN и RENDER_EXTERNAL_URL заданы в Render")

web_app = Flask(__name__)

@web_app.route("/")
def index():
    return "Бот работает!"

@web_app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.update_queue.put_nowait(update)
    return "OK"

async def setup_webhook(app: Application):
    await app.bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook установлен:", WEBHOOK_URL)

app = ( ApplicationBuilder().token(TOKEN).post_init(setup_webhook).build())
app.add_handler(CommandHandler("start", handle_start))
app.add_handler(MessageHandler(filters.ALL & filters.User(ADMIN_ID), handle_admin_reply))
app.add_handler(MessageHandler(filters.ALL & ~filters.User(ADMIN_ID), forward_to_admin))

def run_flask():
    web_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

async def main():
    Thread(target=run_flask).start()  # Запуск Flask в отдельном потоке
    await app.initialize()
    print("➡️ initialize done")
    await app.start()
    print("➡️ start done")

if __name__ == "__main__":
    asyncio.run(main())
