from contextlib import asynccontextmanager
from decimal import Decimal
import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.llm import request_summary
from app.models import Book, Customer
from app.schemas import BookCreate, BookUpdate, CustomerCreate

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Create tables on startup so local SQLite and fresh MySQL instances work without a separate migration step.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    # The assignment expects malformed or missing input to return 400 instead of FastAPI's default 422.
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


def serialize_customer(customer: Customer) -> dict:
    return {
        "id": customer.id,
        "userId": customer.user_id,
        "name": customer.name,
        "phone": customer.phone,
        "address": customer.address,
        "address2": customer.address2,
        "city": customer.city,
        "state": customer.state,
        "zipcode": customer.zipcode,
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
        # Generate the summary before saving so the created book is immediately complete in the database.
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


@app.post("/customers", status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, response: Response, db: Session = Depends(get_db)):
    try:
        existing = db.scalar(select(Customer).where(Customer.user_id == str(payload.userId)))
        if existing:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"message": "This user ID already exists in the system."},
            )

        customer = Customer(
            user_id=str(payload.userId),
            name=payload.name,
            phone=payload.phone,
            address=payload.address,
            address2=payload.address2,
            city=payload.city,
            state=payload.state,
            zipcode=payload.zipcode,
        )
        db.add(customer)
        db.commit()
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"message": "This user ID already exists in the system."},
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to create customer %s: %s", payload.userId, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    db.refresh(customer)
    response.headers["Location"] = f"/customers/{customer.id}"
    return serialize_customer(customer)


@app.get("/customers")
def get_customer_by_user_id(userId: EmailStr = Query(...), db: Session = Depends(get_db)) -> dict:
    try:
        customer = db.scalar(select(Customer).where(Customer.user_id == str(userId)))
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except SQLAlchemyError as exc:
        logger.exception("Failed to fetch customer by userId %s: %s", userId, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return serialize_customer(customer)


@app.get("/customers/{customer_id}")
def get_customer_by_id(customer_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except SQLAlchemyError as exc:
        logger.exception("Failed to fetch customer %s: %s", customer_id, exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return serialize_customer(customer)
