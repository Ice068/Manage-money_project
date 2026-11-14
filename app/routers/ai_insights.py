from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SavingsGoal
from app.routers.dashboard import get_dashboard_summary
from app.routers.savings_goals import _as_read, _net_savings_rate
from app.schemas import AIInsightRequest, AIInsightResponse, AIStatus
from app.services.ai_insights import (
    AIConfigurationError,
    AIProviderError,
    generate_insight,
    get_ai_config,
)

router = APIRouter()


@router.get("/status", response_model=AIStatus)
def get_ai_status():
    api_key, model = get_ai_config()
    return AIStatus(enabled=bool(api_key), model=model)


@router.post("/insights", response_model=AIInsightResponse)
def create_ai_insight(payload: AIInsightRequest, db: Session = Depends(get_db)):
    today = date.today()
    summary = get_dashboard_summary(
        start_date=payload.start_date,
        end_date=payload.end_date,
        db=db,
    )
    metrics = {
        "currency": "THB",
        "period_start": summary.period_start.isoformat(),
        "period_end": summary.period_end.isoformat(),
        "income_satangs": summary.income_satangs,
        "expense_satangs": summary.expense_satangs,
        "net_satangs": summary.net_satangs,
        "current_balance_satangs": summary.current_balance_satangs,
        "average_daily_expense_satangs": summary.average_daily_expense_satangs,
        "runway_days": summary.runway_days,
    }

    if payload.goal_id is not None:
        goal = db.get(SavingsGoal, payload.goal_id)
        if goal is None:
            raise HTTPException(status_code=404, detail="Savings goal not found")
        goal_summary = _as_read(goal, _net_savings_rate(db, today), today)
        metrics["savings_goal"] = {
            "target_amount_satangs": goal_summary.target_amount_satangs,
            "saved_amount_satangs": goal_summary.saved_amount_satangs,
            "amount_remaining_satangs": goal_summary.amount_remaining_satangs,
            "progress_percent": goal_summary.progress_percent,
            "average_daily_net_savings_satangs": (
                goal_summary.average_daily_net_savings_satangs
            ),
            "estimated_days": goal_summary.estimated_days,
            "estimated_date": (
                goal_summary.estimated_date.isoformat()
                if goal_summary.estimated_date is not None
                else None
            ),
        }

    try:
        insight, model = generate_insight(metrics)
    except AIConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except AIProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return AIInsightResponse(insight=insight, model=model)
