import json

from services.crm_service.app.emailer import build_activation_email
from services.customer_service.app.events import serialize_customer_registered_event


def test_customer_registered_event_matches_response_payload():
    payload = {
        "id": 7,
        "userId": "reader@example.com",
        "name": "Reader Example",
        "phone": "123-555-1212",
        "address": "1 Main St",
        "address2": "Apt 2",
        "city": "Pittsburgh",
        "state": "PA",
        "zipcode": "15213",
    }

    event_bytes = serialize_customer_registered_event(payload)

    assert json.loads(event_bytes.decode("utf-8")) == payload


def test_activation_email_body_matches_requirement():
    message = build_activation_email(
        sender_email="store@example.com",
        recipient_email="reader@example.com",
        customer_name="Reader Example",
        andrew_id="dzhu",
    )

    assert message["Subject"] == "Activate your book store account"
    assert message["To"] == "reader@example.com"
    assert message.get_content() == (
        "Dear Reader Example,\n"
        "Welcome to the Book store created by dzhu.\n"
        "Exceptionally this time we won't ask you to click a link to activate your account.\n"
    )
