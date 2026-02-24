import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from .main import runner, run_agent
from .config import TELEGRAM_BOT_TOKEN, APP_NAME

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start command received from {update.effective_user.id}")
    await update.message.reply_text(
        "Hi! I'm your Personal GitHub Manager. Tell me what you'd like to do with your repos!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text = update.message.text
    logger.info(f"Message received from {chat_id}: {text}")

    try:
        # Send a typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # Run the ADK agent
        events = await run_agent(user_id=chat_id, session_id="default_session", message=text)

        for event in events:
            if event.author == "personal_github_manager" and event.content:
                response_text = ""
                if hasattr(event.content, "parts"):
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text

                if response_text:
                    logger.info(f"Sending response to {chat_id}: {response_text[:50]}...")
                    await update.message.reply_text(response_text)
    except Exception as e:
        logger.error(f"Error handling message from {chat_id}: {e}")
        await update.message.reply_text(f"Oops, something went wrong: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(update.effective_chat.id)
    logger.info(f"Callback received from {chat_id}: {query.data}")

    await query.answer()

    data = query.data

    if data.startswith("approve_"):
        session_id = data.replace("approve_", "")
        try:
            await query.edit_message_text(text=f"Approving plan...")
            events = await run_agent(user_id=chat_id, session_id="default_session", message=f"Approved plan for Jules session {session_id}")

            for event in events:
                if event.author == "personal_github_manager" and event.content:
                    response_text = ""
                    if hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if part.text:
                                response_text += part.text
                    if response_text:
                        await context.bot.send_message(chat_id=chat_id, text=response_text)
        except Exception as e:
            logger.error(f"Error handling callback from {chat_id}: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"Failed to approve plan: {e}")

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set! Bot cannot start.")
    else:
        logger.info("Starting Telegram bot polling...")
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        start_handler = CommandHandler('start', start)
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        callback_handler = CallbackQueryHandler(handle_callback)

        application.add_handler(start_handler)
        application.add_handler(msg_handler)
        application.add_handler(callback_handler)

        application.run_polling()
