from __future__ import annotations

from email.message import EmailMessage
import smtplib


def build_activation_email(*, sender_email: str, recipient_email: str, customer_name: str, andrew_id: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Activate your book store account"
    message["From"] = sender_email
    message["To"] = recipient_email
    message.set_content(
        f"Dear {customer_name},\n"
        f"Welcome to the Book store created by {andrew_id}.\n"
        "Exceptionally this time we won't ask you to click a link to activate your account.\n"
    )
    return message


class SmtpEmailSender:
    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        sender_email: str,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_username = smtp_username
        self._smtp_password = smtp_password
        self._sender_email = sender_email

    def send_activation_email(self, *, recipient_email: str, customer_name: str, andrew_id: str) -> None:
        message = build_activation_email(
            sender_email=self._sender_email,
            recipient_email=recipient_email,
            customer_name=customer_name,
            andrew_id=andrew_id,
        )

        with smtplib.SMTP(self._smtp_host, self._smtp_port) as smtp:
            smtp.starttls()
            if self._smtp_username:
                smtp.login(self._smtp_username, self._smtp_password)
            smtp.send_message(message)
