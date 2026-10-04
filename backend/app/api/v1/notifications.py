from datetime import datetime, date, time, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.entities import User, NotificationSetting, Meal
from app.schemas.all_schemas import (
    NotificationSettingsUpdate, NotificationSettingsResponse, MissingMealAlert
)

router = APIRouter(prefix="/notifications", tags=["Proactive Notifications & Quiet Hours"])

@router.get("/settings", response_model=NotificationSettingsResponse)
def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve current notification settings and quiet hours for authenticated user."""
    notif = db.query(NotificationSetting).filter(NotificationSetting.user_id == current_user.id).first()
    if not notif:
        notif = NotificationSetting(
            user_id=current_user.id,
            reminders_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            breakfast_time="09:30",
            lunch_time="14:00",
            dinner_time="21:00",
            snack_time="17:00"
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

    return _format_notif_response(notif)

@router.put("/settings", response_model=NotificationSettingsResponse)
def update_notification_settings(
    update: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update proactive notification preferences, custom meal schedules, and quiet hours."""
    notif = db.query(NotificationSetting).filter(NotificationSetting.user_id == current_user.id).first()
    if not notif:
        notif = NotificationSetting(user_id=current_user.id)
        db.add(notif)

    if update.reminders_enabled is not None:
        notif.reminders_enabled = update.reminders_enabled
    if update.quiet_hours_start is not None:
        notif.quiet_hours_start = update.quiet_hours_start
    if update.quiet_hours_end is not None:
        notif.quiet_hours_end = update.quiet_hours_end
    if update.breakfast_time is not None:
        notif.breakfast_time = update.breakfast_time
    if update.lunch_time is not None:
        notif.lunch_time = update.lunch_time
    if update.dinner_time is not None:
        notif.dinner_time = update.dinner_time
    if update.snack_time is not None:
        notif.snack_time = update.snack_time
    if update.breakfast_enabled is not None:
        notif.breakfast_enabled = update.breakfast_enabled
    if update.lunch_enabled is not None:
        notif.lunch_enabled = update.lunch_enabled
    if update.dinner_enabled is not None:
        notif.dinner_enabled = update.dinner_enabled
    if update.snack_enabled is not None:
        notif.snack_enabled = update.snack_enabled

    db.commit()
    db.refresh(notif)

    return _format_notif_response(notif)

@router.get("/check-missing-meals", response_model=List[MissingMealAlert])
def check_missing_meals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates logged meals today against user-configured schedule.
    Checks quiet hours and returns proactive meal reminder triggers for Android WorkManager.
    """
    notif = db.query(NotificationSetting).filter(NotificationSetting.user_id == current_user.id).first()
    if not notif or not notif.reminders_enabled:
        return []

    now = datetime.now()
    current_time_str = now.strftime("%H:%M")

    # Check if currently inside quiet hours
    is_quiet = _is_time_in_range(current_time_str, notif.quiet_hours_start, notif.quiet_hours_end)
    if is_quiet:
        return []

    # Get meals logged today
    today = date.today()
    logged_meals = db.query(Meal.meal_type).filter(
        Meal.user_id == current_user.id,
        func.date(Meal.logged_at) == today
    ).all()
    logged_types = set(m[0].lower() for m in logged_meals)

    alerts = []
    # Schedule checks: (meal_type, scheduled_time, is_enabled, friendly_msg)
    schedule_checks = [
        ("breakfast", notif.breakfast_time, notif.breakfast_enabled, "🍳 Good morning! Have you had breakfast yet?"),
        ("lunch", notif.lunch_time, notif.lunch_enabled, "🍛 Lunch check-in: What did you have for lunch today?"),
        ("snack", notif.snack_time, notif.snack_enabled, "🍎 Afternoon check-in: Log any snacks or tea you had."),
        ("dinner", notif.dinner_time, notif.dinner_enabled, "🍲 Evening check-in: Don't forget to log your dinner!")
    ]

    for m_type, sched_time, enabled, msg in schedule_checks:
        if not enabled:
            continue
        # Check if current time has passed the scheduled meal time and meal not logged
        if current_time_str >= sched_time and m_type not in logged_types:
            alerts.append(
                MissingMealAlert(
                    meal_type=m_type,
                    scheduled_time=sched_time,
                    message=msg,
                    is_quiet_hours=False
                )
            )

    return alerts

def _is_time_in_range(target_str: str, start_str: str, end_str: str) -> bool:
    """Check if target_str HH:MM falls within start_str and end_str (handles overnight wrap)."""
    try:
        t = datetime.strptime(target_str, "%H:%M").time()
        start = datetime.strptime(start_str, "%H:%M").time()
        end = datetime.strptime(end_str, "%H:%M").time()

        if start <= end:
            return start <= t <= end
        else:
            # Over midnight (e.g. 22:00 to 07:00)
            return t >= start or t <= end
    except ValueError:
        return False

def _format_notif_response(n: NotificationSetting) -> NotificationSettingsResponse:
    return NotificationSettingsResponse(
        user_id=n.user_id,
        reminders_enabled=n.reminders_enabled,
        quiet_hours_start=n.quiet_hours_start,
        quiet_hours_end=n.quiet_hours_end,
        breakfast_time=n.breakfast_time,
        lunch_time=n.lunch_time,
        dinner_time=n.dinner_time,
        snack_time=n.snack_time,
        breakfast_enabled=n.breakfast_enabled,
        lunch_enabled=n.lunch_enabled,
        dinner_enabled=n.dinner_enabled,
        snack_enabled=n.snack_enabled
    )
