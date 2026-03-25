from pydantic import BaseModel, EmailStr, Field, field_validator

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


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
