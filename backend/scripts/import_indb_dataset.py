import argparse
import getpass
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

# The application settings require a signing key even though this script only imports food data.
os.environ.setdefault("SECRET_KEY", "dataset-import-process-only")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import the local nutrition spreadsheets into a Neon PostgreSQL database."
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=PROJECT_ROOT / "DATASET" / "INDB",
        help="Directory containing INDB.xlsx, UK_fct.xlsx, US_fct.xlsx, and Units.xlsx.",
    )
    args = parser.parse_args()

    dataset_dir = args.dataset_dir.resolve()
    required_files = ("INDB.xlsx", "UK_fct.xlsx", "US_fct.xlsx", "Units.xlsx")
    missing_files = [name for name in required_files if not (dataset_dir / name).is_file()]
    if missing_files:
        parser.error(f"Missing required dataset files in {dataset_dir}: {', '.join(missing_files)}")

    database_url = getpass.getpass("Paste the Neon connection string (input hidden): ").strip()
    if not database_url:
        parser.error("A Neon connection string is required.")

    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import sessionmaker

    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        parser.error("The connection string must use PostgreSQL.")
    if not url.host or not url.host.lower().endswith(".neon.tech"):
        parser.error("The connection string host must be a Neon host.")
    if url.query.get("sslmode") not in ("require", "verify-ca", "verify-full"):
        parser.error("Use the Neon connection string with sslmode=require.")

    print(f"Target: {url.host}/{url.database}; dataset: {dataset_dir}")
    confirm = input("Type IMPORT to add missing dataset records to this database: ").strip()
    if confirm != "IMPORT":
        print("Import cancelled.")
        return

    from app.core.database import Base, ensure_recipe_ingredient_quantity_column
    from app.services.ingestion.indb_pipeline import INDBIngestionPipeline

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            food_table_exists = connection.execute(
                text("SELECT to_regclass('public.foods')")
            ).scalar_one()
            if food_table_exists:
                current_count = connection.execute(text("SELECT count(*) FROM foods")).scalar_one()
            else:
                current_count = 0
        print(f"Existing food rows: {current_count}")

        Base.metadata.create_all(bind=engine)
        ensure_recipe_ingredient_quantity_column(engine)
        db_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        with db_factory() as db:
            result = INDBIngestionPipeline(str(dataset_dir)).run_ingestion(db, force=True)
        print(
            "Import complete: "
            f"{result['foods_loaded']} new foods, "
            f"{result['conversions_loaded']} new unit conversions."
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
