import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== CONFIG =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))        # Sizning Telegram ID
CARD_NUMBER = os.getenv("CARD_NUMBER", "8600 0000 0000 0000")
CARD_OWNER = os.getenv("CARD_OWNER", "FULL NAME")
CARD_BANK = os.getenv("CARD_BANK", "Uzcard")
AMOUNT = os.getenv("AMOUNT", "100,000 UZS")       # To'lov summasi

# Pending to'lovlar: {user_id: {order info}}
pending_payments = {}

# ===================== START =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args  # web app dan kelgan parametrlar (?start=order_123)

    order_id = args[0] if args else f"order_{user.id}"

    welcome_text = (
        f"👋 Salom, <b>{user.first_name}</b>!\n\n"
        f"💼 <b>Startup nomi</b> ga xush kelibsiz.\n\n"
        f"📦 Buyurtma: <code>{order_id}</code>\n"
        f"💰 To'lov summasi: <b>{AMOUNT}</b>\n\n"
        "To'lovni amalga oshirish uchun quyidagi tugmani bosing:"
    )

    keyboard = [[InlineKeyboardButton("💳 To'lov qilish", callback_data=f"pay:{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# ===================== TO'LOV TUGMASI =====================
async def payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    order_id = query.data.split(":")[1]

    # Pending ga qo'shamiz
    pending_payments[user.id] = {
        "order_id": order_id,
        "user_name": user.full_name,
        "username": f"@{user.username}" if user.username else "yo'q",
        "user_id": user.id,
        "status": "waiting_payment"
    }

    card_text = (
        "💳 <b>To'lov rekvizitlari:</b>\n\n"
        f"🏦 Bank: <b>{CARD_BANK}</b>\n"
        f"💳 Karta raqami: <code>{CARD_NUMBER}</code>\n"
        f"👤 Egasi: <b>{CARD_OWNER}</b>\n"
        f"💰 Summa: <b>{AMOUNT}</b>\n\n"
        "⚠️ <b>Muhim:</b> To'lov qilganingizdan so'ng chek (screenshot) yuboring yoki "
        "\"✅ To'lov qildim\" tugmasini bosing."
    )

    keyboard = [
        [InlineKeyboardButton("✅ To'lov qildim", callback_data=f"done:{order_id}")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        card_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# ===================== TO'LOV QILINDI =====================
async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    order_id = query.data.split(":")[1]

    if user.id in pending_payments:
        pending_payments[user.id]["status"] = "confirming"

    # Foydalanuvchiga xabar
    await query.edit_message_text(
        "⏳ <b>To'lovingiz tekshirilmoqda...</b>\n\n"
        "Administrator tasdiqlashi bilan sizga xabar yuboriladi.\n"
        "Odatda <b>5-15 daqiqa</b> ichida.",
        parse_mode="HTML"
    )

    # Adminga bildirishnoma
    admin_text = (
        "🔔 <b>Yangi to'lov so'rovi!</b>\n\n"
        f"👤 Foydalanuvchi: <b>{user.full_name}</b>\n"
        f"🔗 Username: @{user.username or 'yo\'q'}\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"📦 Order ID: <code>{order_id}</code>\n"
        f"💰 Summa: <b>{AMOUNT}</b>\n\n"
        "Tasdiqlaysizmi?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm:{user.id}:{order_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject:{user.id}:{order_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Admin ga xabar yuborishda xatolik: {e}")

# ===================== SCREENSHOT QABUL QILISH =====================
async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id not in pending_payments:
        await update.message.reply_text("❗ Avval /start buyrug'ini yuboring.")
        return

    order_info = pending_payments[user.id]
    order_id = order_info.get("order_id", "unknown")
    pending_payments[user.id]["status"] = "confirming"

    # Foydalanuvchiga javob
    await update.message.reply_text(
        "📸 Chekingiz qabul qilindi!\n\n"
        "⏳ Administrator tekshirib, tez orada tasdiqlanadi.",
        parse_mode="HTML"
    )

    # Adminga screenshot + tugmalar
    caption = (
        f"📸 <b>To'lov cheki keldi!</b>\n\n"
        f"👤 {user.full_name}\n"
        f"🔗 @{user.username or 'yo\'q'}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📦 Order: <code>{order_id}</code>\n"
        f"💰 Summa: <b>{AMOUNT}</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm:{user.id}:{order_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject:{user.id}:{order_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=update.message.photo[-1].file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=update.message.document.file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Screenshot yuborishda xatolik: {e}")

# ===================== ADMIN: TASDIQLASH =====================
async def admin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Tasdiqlandi!")

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    parts = query.data.split(":")
    target_user_id = int(parts[1])
    order_id = parts[2]

    # Foydalanuvchiga yuboramiz
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
                f"📦 Order ID: <code>{order_id}</code>\n"
                f"💰 Summa: <b>{AMOUNT}</b>\n\n"
                "✅ Xizmatdan foydalanishingiz mumkin!"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga xabar yuborishda xatolik: {e}")

    # Pending dan o'chiramiz
    pending_payments.pop(target_user_id, None)

    await query.edit_message_text(
        f"✅ <b>Tasdiqlandi!</b>\n\nOrder: <code>{order_id}</code>\nFoydalanuvchi xabardor qilindi.",
        parse_mode="HTML"
    )

# ===================== ADMIN: RAD ETISH =====================
async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("❌ Rad etildi!")

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    parts = query.data.split(":")
    target_user_id = int(parts[1])
    order_id = parts[2]

    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
                f"📦 Order ID: <code>{order_id}</code>\n\n"
                "Muammo bo'lsa admin bilan bog'laning yoki qayta urinib ko'ring.",
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Rad xabari yuborishda xatolik: {e}")

    pending_payments.pop(target_user_id, None)

    await query.edit_message_text(
        f"❌ <b>Rad etildi.</b>\n\nOrder: <code>{order_id}</code>",
        parse_mode="HTML"
    )

# ===================== BEKOR QILISH =====================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    pending_payments.pop(user.id, None)

    await query.edit_message_text(
        "❌ To'lov bekor qilindi.\n\nQayta boshlash uchun /start yuboring."
    )

# ===================== MAIN =====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(payment_handler, pattern=r"^pay:"))
    app.add_handler(CallbackQueryHandler(payment_done, pattern=r"^done:"))
    app.add_handler(CallbackQueryHandler(admin_confirm, pattern=r"^confirm:"))
    app.add_handler(CallbackQueryHandler(admin_reject, pattern=r"^reject:"))
    app.add_handler(CallbackQueryHandler(cancel, pattern=r"^cancel$"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receive_screenshot))

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
