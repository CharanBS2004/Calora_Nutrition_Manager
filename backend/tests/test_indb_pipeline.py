from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.entities import Food, FoodUnitConversion
from app.services.ingestion.indb_pipeline import INDBIngestionPipeline


def _write_dataset(dataset_dir):
    indb = Workbook()
    sheet = indb.active
    sheet.append(["code", "name"])
    row = [None] * 50
    row[0] = "TEST001"
    row[1] = "Test Roti"
    row[4] = 250
    row[5] = 45
    row[6] = 8
    row[7] = 3
    row[9] = 5
    row[42] = "piece"
    row[44] = 100
    row[45] = 18
    row[46] = 3
    row[47] = 1
    row[49] = 2
    sheet.append(row)
    indb.save(dataset_dir / "INDB.xlsx")

    units = Workbook()
    units.active.append(["food", "unit", "equivalent"])
    units.active.append(["Test Roti", "piece", "40 g"])
    units.save(dataset_dir / "Units.xlsx")


def test_force_ingestion_adds_only_missing_foods_and_conversions(tmp_path):
    _write_dataset(tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    pipeline = INDBIngestionPipeline(str(tmp_path))

    with session_factory() as db:
        first = pipeline.run_ingestion(db, force=True)
        first_food_count = db.query(Food).count()
        first_conversion_count = db.query(FoodUnitConversion).count()

        second = pipeline.run_ingestion(db, force=True)

        assert first["details"]["indb_recipes"] == 1
        assert second["foods_loaded"] == 0
        assert second["conversions_loaded"] == 0
        assert db.query(Food).count() == first_food_count
        assert db.query(FoodUnitConversion).count() == first_conversion_count

    engine.dispose()
