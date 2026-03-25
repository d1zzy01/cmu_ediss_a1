from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Customer
from .schemas import CustomerCreate

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Customer Service",
    lifespan=lifespan,
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
        db.refresh(customer)
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
