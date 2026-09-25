import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(recipient: str, token: str) -> None:
    if not settings.password_reset_delivery_ready:
        logger.warning("Password reset email delivery is disabled")
        return

    reset_url = (
        f"{settings.public_app_url.rstrip('/')}"
        f"/members/reset-password/confirm?token={quote(token, safe='')}"
    )
    message = EmailMessage()
    message["Subject"] = "NOVA 会員パスワード再設定"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "NOVA会員のパスワード再設定リクエストを受け付けました。\n\n"
        f"{settings.password_reset_token_minutes}分以内に次のURLを開いてください。\n{reset_url}\n\n"
        "この操作に心当たりがない場合は、このメールを無視してください。"
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
