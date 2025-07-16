import logging
import requests
from sqlalchemy.orm import Session
from . import crud
from .config import settings

logger = logging.getLogger(__name__)

def send_telegram_message(chat_id: str, text: str):
    """Sends a message using the Telegram Bot API."""
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        logger.warning("Cannot send Telegram message: Bot token or chat ID is missing.")
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully sent message to Telegram chat ID {chat_id}.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")

def handle_start_command(db: Session, chat_id: str, text: str):
    """Handles the /start command from a user to link their account."""
    parts = text.split()
    if len(parts) > 1:
        code = parts[1]
        user = crud.get_user_by_telegram_code(db, code=code)
        
        if user:
            # Code is valid, link the account
            user.telegram_chat_id = str(chat_id)
            user.telegram_linking_code = None
            user.telegram_linking_code_expires = None
            db.commit()
            
            reply_text = "✅ Success! Your Telegram account has been linked to your ThreatWatch profile. You will now receive critical alerts here."
            send_telegram_message(chat_id, reply_text)
            logger.info(f"Successfully linked Telegram for user '{user.username}' (Chat ID: {chat_id}).")
        else:
            # Code is invalid or expired
            reply_text = "❌ Linking failed. This code is invalid or has expired. Please generate a new link from your profile settings on the website."
            send_telegram_message(chat_id, reply_text)
            logger.warning(f"Failed linking attempt with invalid code '{code}' for Chat ID {chat_id}.")
    else:
        # User just typed /start without a code
        reply_text = (
            "Welcome to the ThreatWatch Alert Bot!\n\n"
            "To link this chat to your account, please go to your <b>Profile Settings</b> on the website and click 'Link Telegram Account'."
        )
        send_telegram_message(chat_id, reply_text)
