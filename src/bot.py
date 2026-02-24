import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from .main import runner, run_agent
from .config import TELEGRAM_BOT_TOKEN, APP_NAME

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm your Personal GitHub Manager. Tell me what you'd like to do with your repos!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text = update.message.text

    # Send a typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Run the ADK agent
    # For now, we use chat_id as session_id and user_id
    events = await run_agent(user_id=chat_id, session_id="default_session", message=text)

    for event in events:
        if event.author == "personal_github_manager" and event.content:
            # Join parts if it's a list (depends on Event structure)
            # In ADK, event.content is often a Content object
            response_text = ""
            if hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text

            if response_text:
                await update.message.reply_text(response_text)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = str(update.effective_chat.id)
    data = query.data

    if data.startswith("approve_"):
        session_id = data.replace("approve_", "")
        # Send approval to ADK agent
        # We can just run a new message "Approve plan for session {session_id}"
        # Or call the tool directly if we had a more complex setup
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

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set!")
    else:
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        start_handler = CommandHandler('start', start)
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        callback_handler = CallbackQueryHandler(handle_callback)

        application.add_handler(start_handler)
        application.add_handler(msg_handler)
        application.add_handler(callback_handler)

        application.run_polling()
