import logging
from typing import Optional
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from twilio.rest import Client
from .config import settings

logger = logging.getLogger(__name__)

# --- Twilio Client Initialization ---
try:
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER:
        twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        logger.info("✅ Twilio client initialized successfully. SMS notifications are ENABLED.")
    else:
        twilio_client = None
        logger.warning("⚠️ Twilio credentials incomplete. SMS notifications are DISABLED.")
except Exception as e:
    twilio_client = None
    logger.error(f"❌ Failed to initialize Twilio client: {e}")


def send_sms_alert(recipient_number: str, threat_type: str, camera_name: str, risk_score: float):
    """
    Sends an SMS alert. Note: Twilio SMS does not natively support image attachments in the same way,
    so this remains a text-only alert. For images, MMS would be required which is a different API.
    """
    if not twilio_client or not recipient_number:
        logger.warning("Skipping SMS alert: Twilio client not ready or no recipient number provided.")
        return

    logger.info(f"Attempting to send SMS to {recipient_number}...")
    message_body = f"CRITICAL THREAT DETECTED!\nCamera: {camera_name}\nThreat: {threat_type}\nRisk Score: {risk_score:.1f}"
    try:
        message = twilio_client.messages.create(body=message_body, from_=settings.TWILIO_FROM_NUMBER, to=recipient_number)
        logger.info(f"✅ SMS alert sent successfully. SID: {message.sid}")
    except Exception as e:
        logger.error(f"❌ Failed to send SMS alert to {recipient_number}: {e}")


def send_telegram_alert(chat_id: str, threat_type: str, camera_name: str, risk_score: float, image_bytes: Optional[bytes] = None):
    """
    Sends a message with an optional photo using the Telegram Bot API.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        logger.warning("Skipping Telegram alert: Bot token not set or no chat ID provided.")
        return
        
    logger.info(f"Attempting to send Telegram alert to chat ID {chat_id}...")
    caption = f"<b>CRITICAL THREAT DETECTED!</b>\n\n<b>Camera:</b> {camera_name}\n<b>Threat:</b> {threat_type}\n<b>Risk Score:</b> {risk_score:.1f}"
    
    try:
        if image_bytes:
            # If an image is provided, use the sendPhoto endpoint
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto"
            files = {'photo': ('snapshot.jpg', image_bytes, 'image/jpeg')}
            data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}
            response = requests.post(url, files=files, data=data, timeout=15)
        else:
            # Fallback to sending a text message if no image is available
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": caption, "parse_mode": "HTML"}
            response = requests.post(url, json=payload, timeout=10)
            
        response.raise_for_status()
        logger.info(f"✅ Telegram alert sent successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to send Telegram alert to {chat_id}: {e}")


def send_email_alert(recipient_email: str, threat_type: str, camera_name: str, risk_score: float, image_bytes: Optional[bytes] = None):
    """
    Sends an alert via email using SMTP, with an optional image attachment.
    """
    if not all([settings.SMTP_SERVER, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]) or not recipient_email:
        logger.warning("Skipping email alert: SMTP settings incomplete or no recipient email provided.")
        return

    logger.info(f"Attempting to send email alert to {recipient_email}...")
    sender_email = settings.SMTP_USERNAME

    message = MIMEMultipart("related") # Use "related" for embedded images
    message["Subject"] = f"Critical Threat Detected: {threat_type}"
    message["From"] = f"ThreatWatch Alert <{sender_email}>"
    message["To"] = recipient_email

    html_body = f"""
    <html><body>
        <h2 style="color: #c0392b;">Critical Threat Detected!</h2>
        <p><strong>Camera:</strong> {camera_name}</p>
        <p><strong>Threat:</strong> {threat_type}</p>
        <p><strong>Risk Score:</strong> {risk_score:.1f}</p>
        { '<img src="cid:snapshot">' if image_bytes else '' }
    </body></html>
    """
    message.attach(MIMEText(html_body, "html"))

    # Attach the image if it exists
    if image_bytes:
        image = MIMEImage(image_bytes, name="snapshot.jpg")
        image.add_header('Content-ID', '<snapshot>') # For embedding in the email body
        message.attach(image)

    try:
        with smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(sender_email, recipient_email, message.as_string())
            logger.info(f"✅ Email alert sent successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to send email alert to {recipient_email}: {e}")
