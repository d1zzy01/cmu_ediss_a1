from __future__ import annotations

import base64
import json
import time

from fastapi import Header, HTTPException, status

ALLOWED_SUBJECTS = {"starlord", "gamora", "drax", "rocket", "groot"}
EXPECTED_ISSUER = "cmu.edu"


def _decode_payload(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("JWT must contain three parts")

    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload + padding)
    return json.loads(decoded.decode("utf-8"))


def validate_jwt_token(authorization: str | None = Header(default=None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    scheme, _, token = authorization.partition(" ")
    if scheme != "Bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = _decode_payload(token)
        sub = payload["sub"]
        exp = payload["exp"]
        iss = payload["iss"]
    except (KeyError, ValueError, json.JSONDecodeError, UnicodeDecodeError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from None

    if sub not in ALLOWED_SUBJECTS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not isinstance(exp, (int, float)) or exp <= time.time():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if iss != EXPECTED_ISSUER:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return payload
