import os
import logging
from typing import Dict, Any, List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- CONFIG -----------------
BTC_ADDRESS = "bc1qz02e0npyrakucwvwjdcehtxvwg3q7ewrxzpdnx"

PRICE_SILVER = 350  # € total
PRICE_GOLD = 450    # € total
DOWN_PAYMENT_EUR = 100
MAINTENANCE_EUR = 49.99

STORE_NAME = "Kyvarion Bots"
WELCOME_TEXT = (
    f"👋 Welcome to {STORE_NAME}!\n"
    "We build custom Telegram shop bots for sellers & communities.\n\n"
    "Choose an option below:"
)

CONTACT_TELEGRAM = "@kyvarion"
CONTACT_EMAIL = "contact@kyvarion.com"

PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": "silver",
        "label": "🥈 Silver Bot (€350)",
        "price": "€350 total",
        "description": "No AI • Fully customizable • Delivery in 24–48h.",
    },
    {
        "id": "gold",
        "label": "🥇 Gold Bot (€450)",
        "price": "€450 total",
        "description": "AI-powered • Fully customizable • Delivery in 48–72h.",
    },
]

REVIEWS = [
    "⭐ \"Kyvarion Bot doubled my group sales!\" – Alex S.",
    "⭐ \"Looks pro & easy to use.\" – Maria D.",
    "⭐ \"The AI feature saves me hours.\" – Daniel T.",
]

REVIEW_PHOTO_NOTE = (
    "📷 You can display *photo reviews* here: screenshots from your buyers, "
    "product proof, payment receipts — all directly in the bot!"
)


# ----------------- LOGGING -----------------
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("kyvarion-bot")


# ----------------- KEYBOARDS -----------------
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 Our Packages", callback_data="menu_packages")],
        [InlineKeyboardButton("🛠 Maintenance", callback_data="menu_maintenance")],
        [InlineKeyboardButton("⭐ Reviews", callback_data="menu_reviews")],
        [InlineKeyboardButton("📩 Contact", callback_data="menu_contact")],
    ])


def packages_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥈 Order Silver (€350)", callback_data="order_silver")],
        [InlineKeyboardButton("🥇 Order Gold (€450)", callback_data="order_gold")],
        [InlineKeyboardButton("⬅ Back", callback_data="menu_main")],
    ])


def maintenance_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🛒 Order Maintenance (€{MAINTENANCE_EUR}/mo)", callback_data="order_maint")],
        [InlineKeyboardButton("⬅ Back", callback_data="menu_main")],
    ])


def reviews_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Back", callback_data="menu_main")],
    ])


def contact_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✉ Leave My Contact", callback_data="order_contact")],
        [InlineKeyboardButton("⬅ Back", callback_data="menu_main")],
    ])


# ----------------- COMMAND: /start -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.message:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=main_menu_kb())


# ----------------- CALLBACK HANDLER -----------------
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    log.info("Button: %s user=%s", data, update.effective_user.id if update.effective_user else "?")

    if data == "menu_main":
        await _safe_edit(query, WELCOME_TEXT, main_menu_kb())

    elif data == "menu_packages":
        txt = (
            "Choose your bot package:\n\n"
            "🥈 Silver Bot – €350\n"
            " • No AI\n • Fully customizable\n • Ready in 24–48h\n\n"
            "🥇 Gold Bot – €450\n"
            " • With AI (OpenAI integration)\n • Fully customizable\n • Ready in 48–72h"
        )
        await _safe_edit(query, txt, packages_menu_kb())

    elif data == "menu_maintenance":
        txt = (
            f"Monthly Maintenance – €{MAINTENANCE_EUR}\n\n"
            "Includes:\n"
            "• Product / content updates\n"
            "• Feature tweaks\n"
            "• Bug fixes\n"
            "• Priority support"
        )
        await _safe_edit(query, txt, maintenance_menu_kb())

    elif data == "menu_reviews":
        txt = "\n".join(REVIEWS) + "\n\n" + REVIEW_PHOTO_NOTE
        await _safe_edit(query, txt, reviews_menu_kb())

    elif data == "menu_contact":
        txt = (
            "Ready to launch your own bot?\n\n"
            f"Telegram: {CONTACT_TELEGRAM}\n"
            f"Email: {CONTACT_EMAIL}\n\n"
            "Or tap below to leave your contact now."
        )
        await _safe_edit(query, txt, contact_menu_kb())

    # ---- Orders ----
    elif data == "order_silver":
        await _begin_order(query, context, package="Silver", total=PRICE_SILVER)

    elif data == "order_gold":
        await _begin_order(query, context, package="Gold", total=PRICE_GOLD)

    elif data == "order_maint":
        context.user_data["pending_package"] = "Maintenance"
        context.user_data["pending_total"] = MAINTENANCE_EUR
        context.user_data["state"] = "await_email"
        await _safe_edit(
            query,
            f"You selected Maintenance (€{MAINTENANCE_EUR}/month).\n\nPlease enter your email address:",
            None,
        )

    elif data == "order_contact":
        context.user_data["pending_package"] = "Contact"
        context.user_data["pending_total"] = None
        context.user_data["state"] = "await_email"
        await _safe_edit(query, "Please enter your email address:", None)


async def _begin_order(query, context, package: str, total: int):
    """Show down payment instructions + ask for email."""
    context.user_data["pending_package"] = package
    context.user_data["pending_total"] = total
    context.user_data["state"] = "await_email"

    txt = (
        f"{package} Bot – €{total} total.\n\n"
        f"To start your order, please send a *down payment of €{DOWN_PAYMENT_EUR}* in BTC.\n"
        f"BTC address:\n{BTC_ADDRESS}\n\n"
        "After you send the down payment, please paste the TX ID or send a screenshot here.\n\n"
        "First, please enter your *email address* to continue:"
    )
    await _safe_edit(query, txt, None)


# ----------------- TEXT HANDLER -----------------
def _looks_like_email(text: str) -> bool:
    t = text.strip()
    return "@" in t and "." in t and " " not in t and len(t) > 5


def _looks_like_phone(text: str) -> bool:
    digits = "".join(ch for ch in text if ch.isdigit())
    return len(digits) >= 7


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    text = update.message.text.strip()
    log.info("Text from %s (state=%s): %r", update.effective_user.id, state, text)

    # ---- Email step ----
    if state == "await_email":
        if _looks_like_email(text):
            context.user_data["email"] = text
            context.user_data["state"] = "await_phone"
            await update.message.reply_text("Great! Now send me your phone number:")
        else:
            await update.message.reply_text("That doesn't look like an email. Try again:")
        return

    # ---- Phone step ----
    if state == "await_phone":
        if _looks_like_phone(text):
            context.user_data["phone"] = text
            context.user_data["state"] = "await_payment_note"
            await update.message.reply_text(
                "Thanks! If you've sent the down payment, paste the TX ID or say 'done'.\n"
                "If not yet, you can do it now using the BTC address above."
            )
        else:
            await update.message.reply_text("That doesn't look like a phone number. Try again:")
        return

    # ---- Payment confirmation / extra notes ----
    if state == "await_payment_note":
        context.user_data["payment_note"] = text
        context.user_data["state"] = None

        pkg = context.user_data.get("pending_package", "Unknown")
        total = context.user_data.get("pending_total", "n/a")
        email = context.user_data.get("email", "n/a")
        phone = context.user_data.get("phone", "n/a")
        note = context.user_data.get("payment_note", "n/a")

        # log lead
        log.info(
            "LEAD: package=%s total=%s email=%s phone=%s note=%s user_id=%s",
            pkg, total, email, phone, note, update.effective_user.id,
        )

        await update.message.reply_text(
            f"✅ Thanks! We received your info.\n\n"
            f"Package: {pkg}\n"
            f"Email: {email}\n"
            f"Phone: {phone}\n"
            f"Message: {note}\n\n"
            f"If you haven't yet, remember: *€{DOWN_PAYMENT_EUR} BTC* to start.\n"
            f"BTC: {BTC_ADDRESS}\n\n"
            "We will contact you shortly!",
            reply_markup=main_menu_kb(),
        )
        return

    # ---- Fallback ----
    await update.message.reply_text(
        "Use the menu below to browse packages or leave your contact.",
        reply_markup=main_menu_kb(),
    )


# ----------------- SAFE EDIT -----------------
async def _safe_edit(query, text: str, kb: InlineKeyboardMarkup | None):
    try:
        await query.edit_message_text(text=text, reply_markup=kb)
    except Exception as e:
        log.warning("Edit failed (%s). Sending new message.", e)
        await query.message.reply_text(text, reply_markup=kb)


# ----------------- MAIN (WEBHOOK MODE) -----------------
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env var missing. Set it in Render.")

    # Build app
    application = Application.builder().token(token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # Webhook settings for Render
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")  # Render injects this
    if not host:
        # local fallback
        host = "localhost"
    webhook_url = f"https://{host}/{token}"

    log.info("Starting Kyvarion bot webhook on port %s", port)
    log.info("Webhook URL: %s", webhook_url)

    # run_webhook blocks here
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,         # secret path
        webhook_url=webhook_url # public URL Telegram calls
    )


if __name__ == "__main__":
    main()
