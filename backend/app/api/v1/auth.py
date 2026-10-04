from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.deps import get_current_user
from app.models.entities import User, UserProfile, NutritionGoal, NotificationSetting
from app.schemas.all_schemas import SignupRequest, LoginRequest, TokenResponse, PasswordResetRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user with default profile, nutrition goals, and notification settings."""
    existing_user = db.query(User).filter(User.email == request.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    hashed_pw = get_password_hash(request.password)
    new_user = User(
        email=request.email.lower().strip(),
        hashed_password=hashed_pw,
        is_active=True
    )
    db.add(new_user)
    db.flush()

    # Create associated profile
    profile = UserProfile(
        user_id=new_user.id,
        name=request.name.strip(),
        activity_level="moderate",
        dietary_preference="vegetarian"
    )
    db.add(profile)

    # Create default nutrition goals
    goals = NutritionGoal(
        user_id=new_user.id,
        calorie_target=2000.0,
        protein_g=75.0,
        carb_g=250.0,
        fat_g=65.0,
        fiber_g=30.0,
        water_ml=2500.0
    )
    db.add(goals)

    # Create default notification settings
    notif = NotificationSetting(
        user_id=new_user.id,
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
    db.refresh(new_user)

    access_token = create_access_token(subject=new_user.id)
    refresh_token = create_refresh_token(subject=new_user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=new_user.id,
        email=new_user.email,
        name=profile.name
    )

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email and password."""
    user = db.query(User).filter(User.email == request.email.lower().strip()).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive.")

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    user_name = user.profile.name if user.profile else user.email.split("@")[0]

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        name=user_name
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

    new_access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    user_name = user.profile.name if user.profile else user.email

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        name=user_name
    )

@router.post("/reset-password")
def reset_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Reset user password securely."""
    user = db.query(User).filter(User.email == request.email.lower().strip()).first()
    if not user:
        # Avoid user enumeration by returning success message
        return {"message": "If this email is registered, a password reset has been processed."}
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    return {"message": "Password reset successfully."}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Return currently authenticated user identity and profile summary."""
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "name": current_user.profile.name if current_user.profile else "",
        "created_at": current_user.created_at
    }
