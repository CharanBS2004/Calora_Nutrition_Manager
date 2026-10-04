from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.entities import User, Food
from app.schemas.all_schemas import FoodResponse, FoodSearchResponse
from app.services.unit_converter import unit_converter

router = APIRouter(prefix="/foods", tags=["Foods & Nutrition"])

@router.get("/search", response_model=FoodSearchResponse)
def search_foods(
    q: str = Query(..., min_length=1, description="Food name search query (e.g. 'sambar', 'idli', 'rice', 'dal')"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Search Indian foods and dishes from the INDB and ICMR-NIN database."""
    query = db.query(Food).filter(Food.is_custom.is_(False))
    clean_q = q.strip().lower()

    # Search by exact and substring match
    filter_cond = or_(
        Food.food_name.ilike(f"%{clean_q}%"),
        Food.food_code.ilike(f"%{clean_q}%")
    )
    query = query.filter(filter_cond)

    if category:
        query = query.filter(Food.category.ilike(f"%{category}%"))

    total = query.count()
    items = query.order_by(Food.food_name.asc()).offset(offset).limit(limit).all()

    return FoodSearchResponse(
        total=total,
        items=[
            FoodResponse(
                id=f.id,
                food_code=f.food_code,
                food_name=f.food_name,
                category=f.category,
                source=f.source,
                serving_size=f.serving_size,
                serving_unit=f.serving_unit,
                weight_g=f.weight_g,
                energy_kcal=f.energy_kcal,
                protein_g=f.protein_g,
                carbohydrate_g=f.carbohydrate_g,
                fat_g=f.fat_g,
                fiber_g=f.fiber_g,
                unit_serving_energy_kcal=f.unit_serving_energy_kcal,
                unit_serving_protein_g=f.unit_serving_protein_g,
                unit_serving_carbohydrate_g=f.unit_serving_carbohydrate_g,
                unit_serving_fat_g=f.unit_serving_fat_g,
                unit_serving_fiber_g=f.unit_serving_fiber_g,
                is_custom=f.is_custom
            ) for f in items
        ]
    )

@router.get("/categories", response_model=List[str])
def get_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Retrieve all available food categories."""
    cats = db.query(Food.category).distinct().filter(Food.category.isnot(None)).all()
    return sorted([c[0] for c in cats if c[0]])

@router.get("/{food_id}", response_model=FoodResponse)
def get_food(food_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Retrieve complete nutritional information for a specific food."""
    food = db.query(Food).filter(Food.id == food_id).first()
    if not food:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food item not found.")

    return FoodResponse(
        id=food.id,
        food_code=food.food_code,
        food_name=food.food_name,
        category=food.category,
        source=food.source,
        serving_size=food.serving_size,
        serving_unit=food.serving_unit,
        weight_g=food.weight_g,
        energy_kcal=food.energy_kcal,
        protein_g=food.protein_g,
        carbohydrate_g=food.carbohydrate_g,
        fat_g=food.fat_g,
        fiber_g=food.fiber_g,
        unit_serving_energy_kcal=food.unit_serving_energy_kcal,
        unit_serving_protein_g=food.unit_serving_protein_g,
        unit_serving_carbohydrate_g=food.unit_serving_carbohydrate_g,
        unit_serving_fat_g=food.unit_serving_fat_g,
        unit_serving_fiber_g=food.unit_serving_fiber_g,
        is_custom=food.is_custom
    )

@router.get("/convert-unit/check")
def convert_unit(
    food_name: str,
    quantity: float,
    unit: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Calculate gram conversion for food and volume unit using food-specific density factors."""
    grams, is_specific, conf, note = unit_converter.convert_to_grams(
        food_name=food_name,
        quantity=quantity,
        unit=unit,
        db=db,
    )
    return {
        "food_name": food_name,
        "quantity": quantity,
        "unit": unit,
        "grams_calculated": grams,
        "is_density_specific": is_specific,
        "confidence_score": conf,
        "note": note
    }
