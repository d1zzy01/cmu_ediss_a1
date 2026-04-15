from __future__ import annotations

from collections.abc import Mapping

import httpx
from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse

from .auth import validate_jwt_token
from .config import settings

FIELDS_TO_REMOVE = {"address", "address2", "city", "state", "zipcode"}

app = FastAPI(
    title="Mobile BFF Service",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={})


async def forward_request(
    base_url: str,
    method: str,
    path: str,
    *,
    params: Mapping[str, str] | None = None,
    json_body: dict | None = None,
) -> httpx.Response:
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        return await client.request(method, path, params=params, json=json_body)


def transform_book_payload(payload: dict) -> dict:
    transformed = dict(payload)
    if transformed.get("genre") == "non-fiction":
        transformed["genre"] = 3
    return transformed


def transform_customer_payload(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key not in FIELDS_TO_REMOVE}


@app.get("/status", response_class=PlainTextResponse)
async def status_check() -> str:
    return "OK"


@app.post("/books", dependencies=[Depends(validate_jwt_token)])
async def create_book(request: Request) -> Response:
    upstream = await forward_request(
        settings.book_service_url,
        "POST",
        "/books",
        json_body=await request.json(),
    )
    response = JSONResponse(content=upstream.json(), status_code=upstream.status_code)
    if "Location" in upstream.headers:
        response.headers["Location"] = upstream.headers["Location"]
    return response


@app.put("/books/{isbn}", dependencies=[Depends(validate_jwt_token)])
async def update_book(isbn: str, request: Request) -> Response:
    upstream = await forward_request(
        settings.book_service_url,
        "PUT",
        f"/books/{isbn}",
        json_body=await request.json(),
    )
    return JSONResponse(content=upstream.json(), status_code=upstream.status_code)


@app.get("/books/isbn/{isbn}", dependencies=[Depends(validate_jwt_token)])
@app.get("/books/{isbn}", dependencies=[Depends(validate_jwt_token)])
async def get_book(isbn: str) -> Response:
    upstream = await forward_request(settings.book_service_url, "GET", f"/books/{isbn}")
    payload = upstream.json()
    if upstream.status_code == 200:
        payload = transform_book_payload(payload)
    return JSONResponse(content=payload, status_code=upstream.status_code)


@app.get("/books/{isbn}/related-books", dependencies=[Depends(validate_jwt_token)])
async def get_related_books(isbn: str) -> Response:
    upstream = await forward_request(settings.book_service_url, "GET", f"/books/{isbn}/related-books")
    if not upstream.content:
        return Response(status_code=upstream.status_code)
    return JSONResponse(content=upstream.json(), status_code=upstream.status_code)


@app.post("/customers", dependencies=[Depends(validate_jwt_token)])
async def create_customer(request: Request) -> Response:
    upstream = await forward_request(
        settings.customer_service_url,
        "POST",
        "/customers",
        json_body=await request.json(),
    )
    response = JSONResponse(content=upstream.json(), status_code=upstream.status_code)
    if "Location" in upstream.headers:
        response.headers["Location"] = upstream.headers["Location"]
    return response


@app.get("/customers", dependencies=[Depends(validate_jwt_token)])
async def get_customer_by_user_id(request: Request) -> Response:
    upstream = await forward_request(
        settings.customer_service_url,
        "GET",
        "/customers",
        params=dict(request.query_params),
    )
    payload = upstream.json()
    if upstream.status_code == 200:
        payload = transform_customer_payload(payload)
    return JSONResponse(content=payload, status_code=upstream.status_code)


@app.get("/customers/{customer_id}", dependencies=[Depends(validate_jwt_token)])
async def get_customer_by_id(customer_id: int) -> Response:
    upstream = await forward_request(settings.customer_service_url, "GET", f"/customers/{customer_id}")
    payload = upstream.json()
    if upstream.status_code == 200:
        payload = transform_customer_payload(payload)
    return JSONResponse(content=payload, status_code=upstream.status_code)
