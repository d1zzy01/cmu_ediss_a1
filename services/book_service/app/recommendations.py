from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import threading
import time
from typing import Any

import httpx


class RecommendationTimeoutError(Exception):
    pass


class RecommendationCircuitOpenError(Exception):
    pass


class RecommendationServiceError(Exception):
    pass


@dataclass
class RelatedBook:
    isbn: str
    title: str
    authors: str


class CircuitBreakerStateStore:
    def __init__(self, state_path: str, reset_timeout_seconds: float) -> None:
        self._state_path = Path(state_path)
        self._reset_timeout_seconds = reset_timeout_seconds
        self._lock = threading.Lock()

    def get_state(self) -> dict[str, Any]:
        state = self._read_state()
        open_until = float(state.get("open_until", 0.0))
        return {
            "is_open": time.time() < open_until,
            "open_until": open_until,
        }

    def open(self) -> None:
        open_until = time.time() + self._reset_timeout_seconds
        self._write_state({"open_until": open_until})

    def close(self) -> None:
        self._write_state({"open_until": 0.0})

    def _read_state(self) -> dict[str, Any]:
        with self._lock:
            try:
                return json.loads(self._state_path.read_text())
            except FileNotFoundError:
                return {}
            except json.JSONDecodeError:
                return {}

    def _write_state(self, state: dict[str, Any]) -> None:
        with self._lock:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(json.dumps(state))


class RecommendationClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        circuit_breaker_store: CircuitBreakerStateStore,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._circuit_breaker_store = circuit_breaker_store

    def get_related_books(self, isbn: str) -> list[RelatedBook]:
        state = self._circuit_breaker_store.get_state()
        if state["is_open"]:
            raise RecommendationCircuitOpenError

        retry_after_open = state["open_until"] > 0.0

        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout_seconds) as client:
                response = client.get(f"/recommended-titles/isbn/{isbn}")
        except httpx.TimeoutException as exc:
            self._circuit_breaker_store.open()
            if retry_after_open:
                raise RecommendationCircuitOpenError from exc
            raise RecommendationTimeoutError from exc
        except httpx.HTTPError as exc:
            raise RecommendationServiceError from exc

        if not response.is_success:
            raise RecommendationServiceError(
                f"Recommendation service returned unexpected status {response.status_code}"
            )

        self._circuit_breaker_store.close()
        payload = response.json()
        if isinstance(payload, dict):
            payload = [payload]
        return [
            RelatedBook(
                isbn=item["isbn"],
                title=item["title"],
                authors=item["authors"],
            )
            for item in payload
        ]
