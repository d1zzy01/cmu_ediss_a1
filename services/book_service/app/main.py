from contextlib import asynccontextmanager
from decimal import Decimal
import logging

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .llm import request_summary
from .models import Book
from .recommendations import (
    CircuitBreakerStateStore,
    RecommendationCircuitOpenError,
    RecommendationClient,
    RecommendationServiceError,
    RecommendationTimeoutError,
)
from .config import settings
from .schemas import BookCreate, BookUpdate

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Book Service",
    lifespan=lifespan,
)

recommendation_client = RecommendationClient(
    base_url=settings.recommendation_service_url,
    timeout_seconds=settings.recommendation_timeout_seconds,
    circuit_breaker_store=CircuitBreakerStateStore(
        settings.circuit_breaker_state_path,
        settings.circuit_breaker_reset_timeout_seconds,
    ),
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal server error."},
    )


def serialize_book(book: Book) -> dict:
    return {
        "ISBN": book.isbn,
        "title": book.title,
        "Author": book.author,
        "description": book.description,
        "genre": book.genre,
        "price": float(Decimal(book.price)),
        "quantity": book.quantity,
        "summary": book.summary,
    }


@app.get("/status", response_class=PlainTextResponse)
def status_check() -> str:
    return "OK"


@app.post("/books", status_code=status.HTTP_201_CREATED)
def create_book(
    payload: BookCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        existing = db.get(Book, payload.ISBN)
        if existing:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"message": "This ISBN already exists in the system."},
            )

        book = Book(
            isbn=payload.ISBN,
            title=payload.title,
            author=payload.Author,
            description=payload.description,
            genre=payload.genre,
            price=payload.price,
            quantity=payload.quantity,
            summary="",
        )
        book.summary = request_summary(book)
        db.add(book)
        db.commit()
        db.refresh(book)
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"message": "This ISBN already exists in the system."},
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to create book %s: %s", payload.ISBN, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    response.headers["Location"] = f"{str(request.base_url).rstrip('/')}/books/{book.isbn}"
    body = serialize_book(book)
    body.pop("summary", None)
    return body


@app.put("/books/{isbn}")
def update_book(isbn: str, payload: BookUpdate, db: Session = Depends(get_db)) -> dict:
    if isbn != payload.ISBN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        book = db.get(Book, isbn)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        book.title = payload.title
        book.author = payload.Author
        book.description = payload.description
        book.genre = payload.genre
        book.price = payload.price
        book.quantity = payload.quantity
        db.add(book)
        db.commit()
        db.refresh(book)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to update book %s: %s", isbn, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    body = serialize_book(book)
    body.pop("summary", None)
    return body


@app.get("/books/isbn/{isbn}")
@app.get("/books/{isbn}")
def get_book(isbn: str, db: Session = Depends(get_db)) -> dict:
    try:
        book = db.get(Book, isbn)
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except SQLAlchemyError as exc:
        logger.exception("Failed to fetch book %s: %s", isbn, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return serialize_book(book)


@app.get("/books/{isbn}/related-books")
def get_related_books(isbn: str):
    try:
        recommendations = recommendation_client.get_related_books(isbn)
    except RecommendationTimeoutError:
        return Response(status_code=status.HTTP_504_GATEWAY_TIMEOUT)
    except RecommendationCircuitOpenError:
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    except RecommendationServiceError as exc:
        logger.exception("Failed to fetch recommendations for %s: %s", isbn, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY)

    if not recommendations:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return [
        {
            "ISBN": recommendation.isbn,
            "title": recommendation.title,
            "Author": recommendation.authors,
        }
        for recommendation in recommendations
    ]
