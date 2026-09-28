from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class RiskLevel(StrEnum):
    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"


class PaymentEvent(BaseModel):
    occurred_at: datetime
    kind: str = Field(min_length=1)
    amount_usd: Decimal = Field(ge=0)
    reference: str = Field(min_length=1)


class StatementRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    customer_email: str = Field(min_length=3)
    period_start: date
    period_end: date
    risk_level: RiskLevel
    payment_events: list[PaymentEvent] = Field(min_length=1)

    @field_validator("customer_email")
    @classmethod
    def email_has_address_shape(cls, value: str) -> str:
        local, separator, domain = value.partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("customer_email must be a valid email address")
        return value

    @model_validator(mode="after")
    def period_is_ordered(self) -> "StatementRequest":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class StatementResult(BaseModel):
    status: str
    customer_id: str
    pdf_url: str | None = None
    message_id: str | None = None
    reason: str | None = None
