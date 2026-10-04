import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import (
    engine,
    Base,
    SessionLocal,
    ensure_recipe_ingredient_quantity_column,
)
from app.services.ingestion.indb_pipeline import indb_pipeline

# Routers
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.foods import router as foods_router
from app.api.v1.recipes import router as recipes_router
from app.api.v1.meals import router as meals_router
from app.api.v1.health import router as health_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.agent import router as agent_router
from app.api.v1.audio import router as audio_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    ensure_recipe_ingredient_quantity_column()
    db = SessionLocal()
    try:
        indb_pipeline.run_ingestion(db, force=False)
    finally:
        db.close()
    logger.info("Backend services ready.")
    yield
    # Shutdown
    logger.info("Shutting down backend services.")

app = FastAPI(
    title="AI-Powered Personal Nutrition & Energy Balance Coach API",
    description="Agentic AI backend for Indian diet nutrition tracking, recipe building, Health Connect, and proactive coaching.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for mobile clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
api_v1_prefix = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(users_router, prefix=api_v1_prefix)
app.include_router(foods_router, prefix=api_v1_prefix)
app.include_router(recipes_router, prefix=api_v1_prefix)
app.include_router(meals_router, prefix=api_v1_prefix)
app.include_router(health_router, prefix=api_v1_prefix)
app.include_router(notifications_router, prefix=api_v1_prefix)
app.include_router(analytics_router, prefix=api_v1_prefix)
app.include_router(agent_router, prefix=api_v1_prefix)
app.include_router(audio_router, prefix=api_v1_prefix)

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health-check")
def health_check():
    return {"status": "healthy"}
