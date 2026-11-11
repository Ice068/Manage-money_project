from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppSettings, Transaction
from app.schemas import DashboardSettingsRead, DashboardSettingsUpdate, DashboardSummary

router = APIRouter()


def _sum_transactions(db: Session, start_date: date, end_date: date) -> tuple[int, int]:
    income_total = func.coalesce(
        func.sum(
            case(
                (Transaction.type == "income", Transaction.amount_satangs),
                else_=0,
            )
        ),
        0,
    ).label("income_satangs")
    expense_total = func.coalesce(
        func.sum(
            case(
                (Transaction.type == "expense", Transaction.amount_satangs),
                else_=0,
            )
        ),
        0,
    ).label("expense_satangs")
    totals = db.execute(
        select(income_total, expense_total).where(
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
    ).one()
    return int(totals.income_satangs), int(totals.expense_satangs)


def _get_settings(db: Session) -> AppSettings:
    settings = db.get(AppSettings, 1)
    if settings is None:
        first_transaction_date = db.scalar(select(func.min(Transaction.date)))
        settings = AppSettings(
            id=1,
            opening_balance_satangs=0,
            opening_balance_date=first_transaction_date or date.today(),
        )
    return settings


@router.get("/settings", response_model=DashboardSettingsRead)
def get_dashboard_settings(db: Session = Depends(get_db)):
    return _get_settings(db)


@router.put("/settings", response_model=DashboardSettingsRead)
def update_dashboard_settings(
    payload: DashboardSettingsUpdate,
    db: Session = Depends(get_db),
):
    settings = db.get(AppSettings, 1)
    if payload.opening_balance_date > date.today():
        raise HTTPException(status_code=422, detail="opening_balance_date cannot be in the future")
    if settings is None:
        settings = AppSettings(id=1)
        db.add(settings)
    settings.opening_balance_satangs = payload.opening_balance_satangs
    settings.opening_balance_date = payload.opening_balance_date
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    today = date.today()
    period_end = end_date or today
    period_start = start_date or period_end.replace(day=1)

    if period_start > period_end:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")
    if period_end > today:
        raise HTTPException(status_code=422, detail="end_date cannot be in the future")

    income_satangs, expense_satangs = _sum_transactions(
        db, period_start, period_end
    )

    settings = _get_settings(db)
    tracked_income, tracked_expenses = _sum_transactions(
        db, settings.opening_balance_date, today
    )
    current_balance = (
        settings.opening_balance_satangs + tracked_income - tracked_expenses
    )

    period_days = (period_end - period_start).days + 1
    average_daily_expense = (
        float(Decimal(expense_satangs) / Decimal(period_days)) if expense_satangs else None
    )
    if expense_satangs == 0:
        runway_days = None
    elif current_balance <= 0:
        runway_days = 0
    else:
        runway_days = current_balance * period_days // expense_satangs

    return DashboardSummary(
        period_start=period_start,
        period_end=period_end,
        period_days=period_days,
        income_satangs=income_satangs,
        expense_satangs=expense_satangs,
        net_satangs=income_satangs - expense_satangs,
        opening_balance_satangs=settings.opening_balance_satangs,
        opening_balance_date=settings.opening_balance_date,
        current_balance_satangs=current_balance,
        average_daily_expense_satangs=average_daily_expense,
        runway_days=runway_days,
    )
