from __future__ import annotations

import json
import logging

from kafka import KafkaProducer

logger = logging.getLogger(__name__)


def serialize_customer_registered_event(customer_payload: dict) -> bytes:
    return json.dumps(customer_payload).encode("utf-8")


class CustomerEventPublisher:
    def __init__(self, *, brokers: str, topic: str) -> None:
        self._brokers = [broker.strip() for broker in brokers.split(",") if broker.strip()]
        self._topic = topic

    def publish_customer_registered(self, customer_payload: dict) -> None:
        producer = KafkaProducer(
            bootstrap_servers=self._brokers,
            value_serializer=serialize_customer_registered_event,
        )
        try:
            future = producer.send(self._topic, customer_payload)
            future.get(timeout=10)
            producer.flush(timeout=10)
        finally:
            producer.close()

        logger.info(
            "Published customer registered event to topic %s for userId=%s",
            self._topic,
            customer_payload.get("userId"),
        )
