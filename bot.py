import logging
import os
import urllib.parse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Environment variables
TOKEN = os.getenv("8776238868:AAG3POYCQU9ZaZ_Y_QBC2WmPruEjlcirosw")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "7304215296")

# UPI Details
UPI_ID = os.getenv("UPI_ID", "BHARATPE.9N0W0I1H4F585383@unitype")
PAYEE_NAME = "Voucher Store"

# Voucher Inventory / Menu Data
VOUCHERS = {
    "flipkart": {"name": "🛍️ Flipkart ₹500", "price": 450, "stock": 2},
    "shein": {"name": "👗 Shein ₹1000", "price": 850, "stock": 1},
    "abhibus": {"name": "🚌 AbhiBus ₹200", "price": 100, "stock": 1},
    "pvr": {"name": "🎬 PVR ₹300", "price": 250, "stock": 1},
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for key, item in VOUCHERS.items():
        button_text = f"{item['name']} (₹{item['price']})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=key)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "👋 **Voucher Store Bot mein Aapka Swagat hai!**\n\n"
        "Kripya niche se apna voucher select karein:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_key = query.data
    if selected_key in VOUCHERS:
        item = VOUCHERS[selected_key]
        amount = item['price']
        
        # Dynamic UPI Link and QR URL
        upi_url = f"upi://pay?pa={UPI_ID}&pn={urllib.parse.quote(PAYEE_NAME)}&am={amount}&cu=INR"
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(upi_url)}"

        caption = (
            f"📦 **Selected Item:** {item['name']}\n"
            f"💰 **Amount to Pay:** ₹{amount}\n\n"
            f"👉 **Step 1:** Niche diye gaye QR Code par pay karein ya UPI ID copy karein:\n"
            f"📍 **UPI ID:** `{UPI_ID}`\n\n"
            f"👉 **Step 2:** Payment ke baad 12-digit UTR/Txn ID yahan chat mein likhkar bhejye."
        )
        
        # Sent photo with QR code
        await query.message.reply_photo(
            photo=qr_code_url,
            caption=caption,
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.message.from_user
    chat_id = update.message.chat_id

    if text.isdigit() and len(text) == 12:
        await update.message.reply_text(
            f"✅ UTR Received: `{text}`\n\n"
            f"👤 **Aapki Chat ID:** `{chat_id}`\n"
            "Aapka payment verify ho raha hai. Kuch hi der mein aapka voucher code yahan mil jayega!",
            parse_mode="Markdown",
        )
        
        # Admin Alert
        try:
            admin_msg = (
                f"🚨 **New Payment Verification Request!**\n\n"
                f"👤 **User:** {user.full_name} (@{user.username})\n"
                f"🆔 **User Chat ID:** `{chat_id}`\n"
                f"💳 **UTR/Txn ID:** `{text}`"
            )
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Could not send message to admin: {e}")
            
    else:
        await update.message.reply_text("⚠️ Kripya 12-digit ka sahi UTR/Txn ID bhejin.")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()
