import pytest
from fastapi.testclient import TestClient

from services.customer_service.app.database import Base, engine
from services.customer_service.app.main import app


@pytest.fixture(autouse=True)
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_status(client: TestClient) -> None:
    response = client.get("/status")
    assert response.status_code == 200
    assert response.text == "OK"


def test_create_and_get_customer(client: TestClient) -> None:
    payload = {
        "userId": "starlord2002@gmail.com",
        "name": "Star Lord",
        "phone": "+14122144122",
        "address": "48 Galaxy Rd",
        "address2": "suite 4",
        "city": "Fargo",
        "state": "ND",
        "zipcode": "58102",
    }

    create_response = client.post("/customers", json=payload)

    assert create_response.status_code == 201
    customer = create_response.json()
    customer_id = customer["id"]
    assert create_response.headers["Location"] == f"/customers/{customer_id}"

    get_by_id_response = client.get(f"/customers/{customer_id}")
    get_by_user_id_response = client.get("/customers", params={"userId": payload["userId"]})

    assert get_by_id_response.status_code == 200
    assert get_by_user_id_response.status_code == 200
    assert get_by_id_response.json() == customer
    assert get_by_user_id_response.json() == customer


def test_add_customer_twice_returns_422(client: TestClient) -> None:
    payload = {
        "userId": "starlord2002@gmail.com",
        "name": "Star Lord",
        "phone": "+14122144122",
        "address": "48 Galaxy Rd",
        "address2": "suite 4",
        "city": "Fargo",
        "state": "ND",
        "zipcode": "58102",
    }

    first_response = client.post("/customers", json=payload)
    second_response = client.post("/customers", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 422
    assert second_response.json() == {"message": "This user ID already exists in the system."}
