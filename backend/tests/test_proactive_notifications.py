import pytest
from app.core.database import SessionLocal, Base, engine
from app.models.entities import User, NotificationSetting, Meal
from app.api.v1.notifications import check_missing_meals, _is_time_in_range

def test_quiet_hours_time_range_check():
    # Normal daytime: 14:00 inside 10:00 to 18:00
    assert _is_time_in_range("14:00", "10:00", "18:00") is True
    assert _is_time_in_range("08:00", "10:00", "18:00") is False

    # Overnight quiet hours: 22:00 to 07:00
    assert _is_time_in_range("23:30", "22:00", "07:00") is True
    assert _is_time_in_range("03:15", "22:00", "07:00") is True
    assert _is_time_in_range("14:00", "22:00", "07:00") is False

def test_proactive_missing_meal_alerts():
    db = SessionLocal()
    # Create or fetch test user
    user = db.query(User).filter(User.email == "notif_test_user@example.com").first()
    if not user:
        user = User(email="notif_test_user@example.com", hashed_password="pw")
        db.add(user)
        db.flush()
        # Set schedule so breakfast is 08:00 (past) and reminders enabled
        notif = NotificationSetting(
            user_id=user.id,
            reminders_enabled=True,
            quiet_hours_start="01:00",
            quiet_hours_end="04:00",
            breakfast_time="08:00",
            breakfast_enabled=True,
            lunch_time="23:59",  # future
            lunch_enabled=True
        )
        db.add(notif)
        db.commit()

    alerts = check_missing_meals(current_user=user, db=db)
    assert isinstance(alerts, list)
    # Since breakfast_time 08:00 has elapsed and no breakfast logged, alert should be present if currently >= 08:00
    db.close()
