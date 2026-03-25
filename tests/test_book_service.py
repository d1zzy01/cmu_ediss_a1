import pytest
from fastapi.testclient import TestClient

from services.book_service.app.database import Base, engine
from services.book_service.app.main import app


@pytest.fixture(autouse=True)
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "services.book_service.app.main.request_summary",
        lambda book: "Test summary for the created book.",
    )
    with TestClient(app) as test_client:
        yield test_client


def test_status(client: TestClient) -> None:
    response = client.get("/status")
    assert response.status_code == 200
    assert response.text == "OK"


def test_create_and_get_book(client: TestClient) -> None:
    payload = {
        "ISBN": "978-0136886099",
        "title": "Software Architecture in Practice",
        "Author": "Bass, L.",
        "description": "The definitive guide to architecting modern software",
        "genre": "non-fiction",
        "price": 59.95,
        "quantity": 106,
    }

    create_response = client.post("/books", json=payload)

    assert create_response.status_code == 201
    assert create_response.headers["Location"].endswith("/books/978-0136886099")
    assert create_response.json() == payload

    get_response = client.get("/books/978-0136886099")

    assert get_response.status_code == 200
    assert get_response.json()["summary"] == "Test summary for the created book."


def test_add_book_twice_returns_422(client: TestClient) -> None:
    payload = {
        "ISBN": "978-0136886099",
        "title": "Software Architecture in Practice",
        "Author": "Bass, L.",
        "description": "The definitive guide to architecting modern software",
        "genre": "non-fiction",
        "price": 59.95,
        "quantity": 106,
    }

    first_response = client.post("/books", json=payload)
    second_response = client.post("/books", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 422
    assert second_response.json() == {"message": "This ISBN already exists in the system."}


def test_update_book(client: TestClient) -> None:
    payload = {
        "ISBN": "978-0136886099",
        "title": "Software Architecture in Practice",
        "Author": "Bass, L.",
        "description": "The definitive guide to architecting modern software",
        "genre": "non-fiction",
        "price": 59.95,
        "quantity": 106,
    }
    updated_payload = {**payload, "quantity": 99}

    client.post("/books", json=payload)
    update_response = client.put("/books/978-0136886099", json=updated_payload)

    assert update_response.status_code == 200
    assert update_response.json() == updated_payload
