from fastapi.testclient import TestClient

from services.book_service.app import main
from services.book_service.app.recommendations import (
    CircuitBreakerStateStore,
    RecommendationCircuitOpenError,
    RecommendationClient,
    RecommendationTimeoutError,
)


class StubRecommendationClient:
    def __init__(self, *, result=None, error: Exception | None = None):
        self._result = result if result is not None else []
        self._error = error

    def get_related_books(self, isbn: str):
        if self._error:
            raise self._error
        return self._result


def test_related_books_returns_mapped_recommendations(monkeypatch):
    monkeypatch.setattr(
        main,
        "recommendation_client",
        StubRecommendationClient(
            result=[
                type(
                    "RelatedBook",
                    (),
                    {
                        "isbn": "978-0321815736",
                        "title": "Software Architecture in Practice",
                        "authors": "Bass, L.",
                    },
                )(),
                type(
                    "RelatedBook",
                    (),
                    {
                        "isbn": "978-0-321-55268-6",
                        "title": "Documenting Software Architectures Second Edition",
                        "authors": "Clements, P. et al",
                    },
                )(),
            ]
        ),
    )

    response = TestClient(main.app).get("/books/9780134757599/related-books")

    assert response.status_code == 200
    assert response.json() == [
        {
            "ISBN": "978-0321815736",
            "title": "Software Architecture in Practice",
            "Author": "Bass, L.",
        },
        {
            "ISBN": "978-0-321-55268-6",
            "title": "Documenting Software Architectures Second Edition",
            "Author": "Clements, P. et al",
        },
    ]


def test_related_books_returns_204_when_empty(monkeypatch):
    monkeypatch.setattr(main, "recommendation_client", StubRecommendationClient(result=[]))

    response = TestClient(main.app).get("/books/9780134757599/related-books")

    assert response.status_code == 204
    assert response.content == b""


def test_related_books_returns_504_on_timeout(monkeypatch):
    monkeypatch.setattr(
        main,
        "recommendation_client",
        StubRecommendationClient(error=RecommendationTimeoutError()),
    )

    response = TestClient(main.app).get("/books/9780134757599/related-books")

    assert response.status_code == 504
    assert response.content == b""


def test_related_books_returns_503_when_circuit_is_open(monkeypatch):
    monkeypatch.setattr(
        main,
        "recommendation_client",
        StubRecommendationClient(error=RecommendationCircuitOpenError()),
    )

    response = TestClient(main.app).get("/books/9780134757599/related-books")

    assert response.status_code == 503
    assert response.content == b""


def test_recommendation_retry_after_open_timeout_stays_open_and_returns_503(tmp_path):
    state_store = CircuitBreakerStateStore(
        str(tmp_path / "circuit.json"),
        reset_timeout_seconds=60.0,
    )
    state_store.close()
    state_store._write_state({"open_until": 1.0})

    client = RecommendationClient(
        base_url="http://recommendation-service:8000",
        timeout_seconds=3.0,
        circuit_breaker_store=state_store,
    )

    from services.book_service.app import recommendations

    class TimeoutClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url):
            raise recommendations.httpx.TimeoutException("timed out")

    previous_client = recommendations.httpx.Client
    recommendations.httpx.Client = TimeoutClient
    try:
        try:
            client.get_related_books("9780134757599")
            assert False, "expected RecommendationCircuitOpenError"
        except RecommendationCircuitOpenError:
            pass
    finally:
        recommendations.httpx.Client = previous_client

    assert state_store.get_state()["is_open"] is True
