from decimal import Decimal

from pydantic import BaseModel, field_validator


class BookBase(BaseModel):
    ISBN: str
    title: str
    Author: str
    description: str
    genre: str
    price: Decimal
    quantity: int

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("price must be non-negative")
        normalized = int(value.as_tuple().exponent)
        if normalized < -2:
            raise ValueError("price must have 0-2 decimal places")
        return value.quantize(Decimal("0.01"))

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        if value < 0:
            raise ValueError("quantity must be non-negative")
        return value


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    pass
