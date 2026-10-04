from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.entities import User, HealthRecord, Meal
from app.schemas.all_schemas import HealthRecordCreate, HealthRecordResponse, EnergyBalanceResponse
from app.services.nutrition_engine import nutrition_engine

router = APIRouter(prefix="/health", tags=["Health Connect & Energy Balance"])

@router.post("/records", response_model=HealthRecordResponse)
def sync_health_record(
    record_in: HealthRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ingest or update actual physical activity and calories burned from Android Health Connect.
    Never fabricates missing data; clearly attributes source.
    """
    record = db.query(HealthRecord).filter(
        HealthRecord.user_id == current_user.id,
        HealthRecord.recorded_date == record_in.recorded_date
    ).first()

    if not record:
        record = HealthRecord(
            user_id=current_user.id,
            recorded_date=record_in.recorded_date,
            total_calories_burned=record_in.total_calories_burned,
            active_calories_burned=record_in.active_calories_burned,
            steps=record_in.steps,
            distance_m=record_in.distance_m,
            active_minutes=record_in.active_minutes,
            resting_heart_rate=record_in.resting_heart_rate,
            source=record_in.source or "health_connect"
        )
        db.add(record)
    else:
        record.total_calories_burned = record_in.total_calories_burned
        record.active_calories_burned = record_in.active_calories_burned
        record.steps = record_in.steps
        record.distance_m = record_in.distance_m
        record.active_minutes = record_in.active_minutes
        record.resting_heart_rate = record_in.resting_heart_rate
        record.source = record_in.source or "health_connect"

    db.commit()
    db.refresh(record)

    return HealthRecordResponse(
        user_id=record.user_id,
        recorded_date=record.recorded_date,
        total_calories_burned=record.total_calories_burned,
        active_calories_burned=record.active_calories_burned,
        steps=record.steps,
        distance_m=record.distance_m,
        active_minutes=record.active_minutes,
        resting_heart_rate=record.resting_heart_rate,
        source=record.source
    )

@router.get("/records", response_model=List[HealthRecordResponse])
def get_health_records(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve Health Connect records for authenticated user."""
    query = db.query(HealthRecord).filter(HealthRecord.user_id == current_user.id)
    if start_date:
        query = query.filter(HealthRecord.recorded_date >= start_date)
    if end_date:
        query = query.filter(HealthRecord.recorded_date <= end_date)

    records = query.order_by(HealthRecord.recorded_date.desc()).all()
    return [
        HealthRecordResponse(
            user_id=r.user_id,
            recorded_date=r.recorded_date,
            total_calories_burned=r.total_calories_burned,
            active_calories_burned=r.active_calories_burned,
            steps=r.steps,
            distance_m=r.distance_m,
            active_minutes=r.active_minutes,
            resting_heart_rate=r.resting_heart_rate,
            source=r.source
        ) for r in records
    ]

@router.get("/energy-balance", response_model=EnergyBalanceResponse)
def get_energy_balance(
    target_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate Energy Balance = Calories In (Food) vs Calories Out (Health Connect Burned).
    Clearly specifies attribution of calorie expenditure.
    """
    t_date = target_date or date.today()

    # 1. Calories In (Food)
    meals = db.query(Meal).filter(
        Meal.user_id == current_user.id,
        func.date(Meal.logged_at) == t_date
    ).all()
    consumed_kcal = sum(m.total_calories for m in meals)

    # 2. Calories Out (Health Connect)
    health_record = db.query(HealthRecord).filter(
        HealthRecord.user_id == current_user.id,
        HealthRecord.recorded_date == t_date
    ).first()

    if health_record and health_record.total_calories_burned > 0:
        burned_kcal = health_record.total_calories_burned
        source_label = "Android Health Connect (Actual Device Telemetry)"
    else:
        # If no Health Connect data, calculate estimated Basal Metabolic Rate (BMR) from profile
        profile = current_user.profile
        bmr = 2000.0  # default baseline
        if profile and profile.weight_kg and profile.height_cm and profile.age:
            # Mifflin-St Jeor equation baseline
            if profile.gender and profile.gender.lower() == "female":
                bmr = (10 * profile.weight_kg) + (6.25 * profile.height_cm) - (5 * profile.age) - 161
            else:
                bmr = (10 * profile.weight_kg) + (6.25 * profile.height_cm) - (5 * profile.age) + 5
            # Apply activity multiplier
            act_mult = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
            mult = act_mult.get((profile.activity_level or "moderate").lower(), 1.4)
            bmr = round(bmr * mult, 1)

        burned_kcal = bmr
        source_label = "Estimated Maintenance Burn (Profile BMR Estimation)"

    balance = nutrition_engine.calculate_energy_balance(
        calories_consumed=consumed_kcal,
        calories_burned=burned_kcal
    )

    return EnergyBalanceResponse(
        target_date=t_date,
        calories_consumed=balance["calories_consumed"],
        calories_burned=balance["calories_burned"],
        net_balance_kcal=balance["net_balance_kcal"],
        burned_source=source_label,
        status=balance["status"]
    )
