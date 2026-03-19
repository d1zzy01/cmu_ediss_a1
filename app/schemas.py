from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


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
        # The spec allows at most two decimal places for price.
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


class CustomerCreate(BaseModel):
    userId: EmailStr
    name: str
    phone: str
    address: str
    address2: str | None = None
    city: str
    state: str = Field(min_length=2, max_length=2)
    zipcode: str

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        upper = value.upper()
        if upper not in US_STATES:
            raise ValueError("state must be a valid 2-letter US state abbreviation")
        return upper
