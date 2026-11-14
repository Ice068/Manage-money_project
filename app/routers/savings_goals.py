from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppSettings, SavingsGoal, Transaction
from app.schemas import SavingsGoalCreate, SavingsGoalRead, SavingsGoalUpdate

router = APIRouter()


def _net_savings_rate(db: Session, today: date) -> tuple[int, int] | None:
    settings = db.get(AppSettings, 1)
    start_date = settings.opening_balance_date if settings else None
    if start_date is None:
        start_date = db.scalar(select(func.min(Transaction.date))) or today
    if start_date > today:
        return None

    totals = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == "income", Transaction.amount_satangs),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == "expense", Transaction.amount_satangs),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(
            Transaction.date >= start_date,
            Transaction.date <= today,
        )
    ).one()
    net_savings = int(totals[0]) - int(totals[1])
    if net_savings <= 0:
        return None

    elapsed_days = (today - start_date).days + 1
    return net_savings, elapsed_days


def _as_read(goal: SavingsGoal, savings_rate: tuple[int, int] | None, today: date):
    remaining = max(0, goal.target_amount_satangs - goal.saved_amount_satangs)
    progress = min(100.0, goal.saved_amount_satangs / goal.target_amount_satangs * 100)
    average_daily_net = (
        savings_rate[0] / savings_rate[1] if savings_rate is not None else None
    )
    if remaining == 0:
        estimated_days = 0
        estimated_date = today
    elif savings_rate is None:
        estimated_days = None
        estimated_date = None
    else:
        net_savings, elapsed_days = savings_rate
        estimated_days = (remaining * elapsed_days + net_savings - 1) // net_savings
        estimated_date = today + timedelta(days=estimated_days)

    return SavingsGoalRead(
        id=goal.id,
        name=goal.name,
        target_amount_satangs=goal.target_amount_satangs,
        saved_amount_satangs=goal.saved_amount_satangs,
        note=goal.note,
        created_at=goal.created_at,
        amount_remaining_satangs=remaining,
        progress_percent=progress,
        average_daily_net_savings_satangs=average_daily_net,
        estimated_days=estimated_days,
        estimated_date=estimated_date,
    )


@router.get("", response_model=list[SavingsGoalRead])
def list_savings_goals(db: Session = Depends(get_db)):
    today = date.today()
    savings_rate = _net_savings_rate(db, today)
    statement = select(SavingsGoal).order_by(
        SavingsGoal.created_at.desc(),
        SavingsGoal.id.desc(),
    )
    goals = db.scalars(statement)
    return [_as_read(goal, savings_rate, today) for goal in goals]


@router.post("", response_model=SavingsGoalRead, status_code=status.HTTP_201_CREATED)
def create_savings_goal(payload: SavingsGoalCreate, db: Session = Depends(get_db)):
    goal = SavingsGoal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    today = date.today()
    return _as_read(goal, _net_savings_rate(db, today), today)


@router.get("/{goal_id}", response_model=SavingsGoalRead)
def get_savings_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.get(SavingsGoal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    today = date.today()
    return _as_read(goal, _net_savings_rate(db, today), today)


@router.put("/{goal_id}", response_model=SavingsGoalRead)
def update_savings_goal(
    goal_id: int,
    payload: SavingsGoalUpdate,
    db: Session = Depends(get_db),
):
    goal = db.get(SavingsGoal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    for field, value in payload.model_dump().items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    today = date.today()
    return _as_read(goal, _net_savings_rate(db, today), today)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_savings_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.get(SavingsGoal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    db.delete(goal)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
