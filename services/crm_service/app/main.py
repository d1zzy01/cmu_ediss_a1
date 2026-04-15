from __future__ import annotations

import json
import logging

from kafka import KafkaConsumer

from .config import settings
from .emailer import SmtpEmailSender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=[broker.strip() for broker in settings.kafka_brokers.split(",") if broker.strip()],
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id=f"{settings.andrew_id}-crm",
    )


def run() -> None:
    email_sender = SmtpEmailSender(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password,
        sender_email=settings.sender_email,
    )
    consumer = create_consumer()
    logger.info("CRM consumer started for topic %s", settings.kafka_topic)

    for message in consumer:
        payload = message.value
        logger.info("Received customer registered event for userId=%s", payload.get("userId"))
        email_sender.send_activation_email(
            recipient_email=payload["userId"],
            customer_name=payload["name"],
            andrew_id=settings.andrew_id,
        )


if __name__ == "__main__":
    run()
