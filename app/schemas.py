from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_AMOUNT_SATANGS = 1_000_000_000_000


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["income", "expense"]
    amount_satangs: int = Field(gt=0, le=MAX_AMOUNT_SATANGS)
    date: date
    category: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)


class TransactionUpdate(TransactionCreate):
    pass


class TransactionRead(TransactionCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    created_at: datetime


class DashboardSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opening_balance_satangs: int = Field(ge=0, le=MAX_AMOUNT_SATANGS)
    opening_balance_date: date


class DashboardSettingsRead(DashboardSettingsUpdate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class DashboardSummary(BaseModel):
    period_start: date
    period_end: date
    period_days: int
    income_satangs: int
    expense_satangs: int
    net_satangs: int
    opening_balance_satangs: int
    opening_balance_date: date
    current_balance_satangs: int
    average_daily_expense_satangs: float | None
    runway_days: int | None


class SavingsGoalFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    target_amount_satangs: int = Field(gt=0, le=MAX_AMOUNT_SATANGS)
    saved_amount_satangs: int = Field(ge=0, le=MAX_AMOUNT_SATANGS)
    note: str | None = Field(default=None, max_length=500)


class SavingsGoalCreate(SavingsGoalFields):
    pass


class SavingsGoalUpdate(SavingsGoalFields):
    pass


class SavingsGoalRead(SavingsGoalFields):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)

    id: int
    created_at: datetime
    amount_remaining_satangs: int
    progress_percent: float
    average_daily_net_savings_satangs: float | None
    estimated_days: int | None
    estimated_date: date | None


class AIInsightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date | None = None
    end_date: date | None = None
    goal_id: int | None = Field(default=None, gt=0)


class AIInsightResponse(BaseModel):
    insight: str
    model: str


class AIStatus(BaseModel):
    enabled: bool
    model: str
