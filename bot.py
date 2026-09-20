import logging
import qrcode
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
BOT_TOKEN = "8776238868:AAHxc2IcPYO7kYKih078nix9j6-3TfIkrxk"      # BotFather Token
ADMIN_ID = 7304215296                  # Aapki Admin ID
MERCHANT_UPI = "BHARATPE.9N0W0I1H4F585383@unitype" # Aapka Merchant UPI ID

WAITING_FOR_UTR = 1

# Category Details, Prices & Stock
VOUCHERS = {
    "flipkart": {"name": "Flipkart ₹500 Gift Card", "price": 450, "codes": ["FK-SAMPLE-101", "FK-SAMPLE-102"]},
    "shein": {"name": "Shein ₹1000 Voucher", "price": 850, "codes": ["SHEIN-9988-X"]},
    "abhibus": {"name": "AbhiBus ₹200 Discount", "price": 100, "codes": ["ABHI-BUS-200"]},
    "pvr": {"name": "PVR Movie Voucher ₹300", "price": 250, "codes": ["PVR-MOV-300"]}
}

PENDING_ORDERS = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for key, item in VOUCHERS.items():
        stock_count = len(item["codes"])
        keyboard.append([
            InlineKeyboardButton(f"{item['name']} (₹{item['price']}) - Stock: {stock_count}", callback_data=f'buy_{key}')
        ])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 **Voucher Store Bot mein Aapka Swagat hai!**\n\nKripya niche se apna voucher select karein:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("buy_"):
        item_key = data.split("_")[1]
        item = VOUCHERS.get(item_key)

        if len(item["codes"]) == 0:
            await query.message.reply_text("❌ Ye voucher abhi Out of Stock hai! Kripya baad mein try karein.")
            return ConversationHandler.END

        context.user_data['selected_item'] = item_key

        upi_url = f"upi://pay?pa={MERCHANT_UPI}&pn=VoucherStore&am={item['price']}&cu=INR"
        qr = qrcode.make(upi_url)
        bio = BytesIO()
        bio.name = 'qr.png'
        qr.save(bio, 'PNG')
        bio.seek(0)

        msg = (
            f"📦 **Selected Item:** {item['name']}\n"
            f"💰 **Amount to Pay:** ₹{item['price']}\n\n"
            f"👉 Step 1: QR Code par pay karein (UPI ID: `{MERCHANT_UPI}`).\n"
            f"👉 Step 2: Payment ke baad **12-digit UTR/Txn ID** yahan chat mein likhkar bhejye."
        )
        await query.message.reply_photo(photo=bio, caption=msg, parse_mode='Markdown')
        return WAITING_FOR_UTR

async def receive_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    utr = update.message.text.strip()
    user = update.message.from_user
    item_key = context.user_data.get('selected_item')
    item = VOUCHERS.get(item_key)

    if not item or len(item["codes"]) == 0:
        await update.message.reply_text("Kuch error hua ya stock khatam ho gaya. /start dabayein.")
        return ConversationHandler.END

    order_id = f"{user.id}_{utr}"
    PENDING_ORDERS[order_id] = {
        "user_id": user.id,
        "item_key": item_key,
        "utr": utr
    }

    admin_keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{order_id}")
        ]
    ]
    admin_msg = (
        f"🚨 **New Payment Request!**\n\n"
        f"👤 **User:** {user.full_name} (@{user.username})\n"
        f"🆔 **User ID:** `{user.id}`\n"
        f"📦 **Voucher:** {item['name']}\n"
        f"💵 **Price:** ₹{item['price']}\n"
        f"🔢 **UTR Number:** `{utr}`"
    )
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_msg,
        reply_markup=InlineKeyboardMarkup(admin_keyboard),
        parse_mode='Markdown'
    )

    await update.message.reply_text(
        "✅ **Aapka UTR submit ho gaya hai!**\n\nAdmin verification ke baad instant voucher bhej diya jayega."
    )
    return ConversationHandler.END

async def admin_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_"):
        order_id = data.replace("approve_", "")
        order = PENDING_ORDERS.get(order_id)

        if order:
            user_id = order["user_id"]
            item_key = order["item_key"]
            item = VOUCHERS.get(item_key)

            if len(item["codes"]) > 0:
                # Stock se pehla code nikal kar send karein aur delete karein
                voucher_code = item["codes"].pop(0)

                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 **Payment Verified!**\n\nAapka Voucher Code ye raha:\n🎫 `{voucher_code}`",
                    parse_mode='Markdown'
                )
                await query.edit_message_text(f"✅ Approved for User `{user_id}` | Code Delivered: `{voucher_code}`")
            else:
                await query.edit_message_text("❌ Stock Khatam Ho Gaya Hai!")
            
            del PENDING_ORDERS[order_id]

    elif data.startswith("reject_"):
        order_id = data.replace("reject_", "")
        order = PENDING_ORDERS.get(order_id)

        if order:
            user_id = order["user_id"]
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ **Payment Verification Failed!**\nUTR match nahi hua."
            )
            await query.edit_message_text(f"❌ Rejected for User `{user_id}`")
            del PENDING_ORDERS[order_id]

# --- ADMIN COMMANDS ---
async def admin_add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    
    try:
        category = context.args[0].lower()
        code = context.args[1]

        if category in VOUCHERS:
            VOUCHERS[category]["codes"].append(code)
            await update.message.reply_text(f"✅ `{code}` added to `{category}` stock!\nTotal Stock: {len(VOUCHERS[category]['codes'])}", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Category not found. Valid ones: {list(VOUCHERS.keys())}")
    except IndexingError:
        await update.message.reply_text("Usage: `/addcode <flipkart/shein/abhibus/pvr> <code>`", parse_mode='Markdown')

async def admin_set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    
    try:
        category = context.args[0].lower()
        price = int(context.args[1])

        if category in VOUCHERS:
            VOUCHERS[category]["price"] = price
            await update.message.reply_text(f"✅ Price updated for `{category}` to ₹{price}!", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Category not found.")
    except Exception:
        await update.message.reply_text("Usage: `/setprice <flipkart/shein/abhibus/pvr> <new_price>`", parse_mode='Markdown')

async def admin_check_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    
    stock_text = "📊 **Current Stock & Prices:**\n\n"
    for key, item in VOUCHERS.items():
        stock_text += f"🔹 **{item['name']}** (`{key}`):\n Price: ₹{item['price']} | Stock: {len(item['codes'])}\n\n"
    
    await update.message.reply_text(stock_text, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^buy_")],
        states={
            WAITING_FOR_UTR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_utr)]
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addcode", admin_add_code))
    app.add_handler(CommandHandler("setprice", admin_set_price))
    app.add_handler(CommandHandler("stock", admin_check_stock))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_action_handler, pattern="^(approve_|reject_)"))

    print("Bot Successfully Chalu Ho Gaya Hai...")
    app.run_polling()


import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is running live!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

Thread(target=run).start()
