from datetime import date, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.entities import User
from app.schemas.all_schemas import DailyAnalytics, AnalyticsReport
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics & Trends"])

@router.get("/daily", response_model=DailyAnalytics)
def get_daily(
    target_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve full day nutrition, macro targets vs actuals, meal distribution, and energy balance."""
    t_date = target_date or date.today()
    return analytics_service.get_daily_analytics(
        user_id=current_user.id,
        target_date=t_date,
        db=db
    )

@router.get("/weekly", response_model=AnalyticsReport)
def get_weekly(
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve weekly nutrition averages, goal adherence, top foods, and daily trend series."""
    return analytics_service.get_period_report(
        user_id=current_user.id,
        period="weekly",
        end_date=end_date,
        db=db
    )

@router.get("/monthly", response_model=AnalyticsReport)
def get_monthly(
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve monthly macro averages, logging consistency, and long-term trend breakdown."""
    return analytics_service.get_period_report(
        user_id=current_user.id,
        period="monthly",
        end_date=end_date,
        db=db
    )

@router.get("/comparison")
def get_comparisons(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compare Today vs Yesterday, This Week vs Previous Week, and This Month vs Previous Month.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    today_data = analytics_service.get_daily_analytics(current_user.id, today, db)
    yest_data = analytics_service.get_daily_analytics(current_user.id, yesterday, db)

    weekly_report = analytics_service.get_period_report(current_user.id, "weekly", today, db)
    monthly_report = analytics_service.get_period_report(current_user.id, "monthly", today, db)

    cal_today = today_data["calories"]["consumed"]
    cal_yest = yest_data["calories"]["consumed"]
    day_cal_delta = round(((cal_today - cal_yest) / max(cal_yest, 1.0)) * 100.0, 1) if cal_yest > 0 else 0.0

    prot_today = today_data["protein_g"]["consumed"]
    prot_yest = yest_data["protein_g"]["consumed"]
    day_prot_delta = round(((prot_today - prot_yest) / max(prot_yest, 1.0)) * 100.0, 1) if prot_yest > 0 else 0.0

    return {
        "today_vs_yesterday": {
            "calories": {"today": cal_today, "yesterday": cal_yest, "delta_percent": day_cal_delta},
            "protein": {"today": prot_today, "yesterday": prot_yest, "delta_percent": day_prot_delta}
        },
        "this_week_vs_last_week": weekly_report.get("comparison_previous_period"),
        "this_month_vs_last_month": monthly_report.get("comparison_previous_period")
    }
