import httpx
from .config import TELEGRAM_BOT_TOKEN
import logging

logger = logging.getLogger(__name__)

async def send_telegram_message(chat_id: str, text: str):
    """Sends a message to the Telegram user using the raw HTTP API."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No Telegram token available, skipping message.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
