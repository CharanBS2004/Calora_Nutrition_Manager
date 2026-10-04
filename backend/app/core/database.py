from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Configure SQLite vs PostgreSQL connection options
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_recipe_ingredient_quantity_column() -> None:
    """Add the submitted recipe amount without disturbing existing gram records."""
    columns = {
        column["name"]
        for column in inspect(engine).get_columns("recipe_ingredients")
    }
    if "quantity" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE recipe_ingredients ADD COLUMN quantity FLOAT")
            )


def get_db():
    """Dependency for obtaining database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
