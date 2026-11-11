from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["income", "expense"]
    amount_satangs: int = Field(gt=0)
    date: date
    category: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)


class TransactionUpdate(TransactionCreate):
    pass


class TransactionRead(TransactionCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    created_at: datetime
