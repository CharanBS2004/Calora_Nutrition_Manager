# Data Ingestion & Nutrition Pipeline

## Indian Nutrient Databank (INDB) & Volumetric Density Resolution

---

## 1. Overview of Data Sources

The primary nutritional grounding of this application is derived from authentic Indian laboratory analyses and regional food composition tables:

| Source Name | File Reference | Food Items Loaded | Description |
| :--- | :--- | :--- | :--- |
| **INDB Recipes** | `DATASET/INDB/recipes.xlsx` & `recipes_names.xlsx` | 1,014 | Authentic Indian cooked recipes across diverse regional cuisines |
| **UK FCT** | `DATASET/INDB/UK_fct.xlsx` | 144 | UK Food Composition Table items curated for South Asian diaspora foods |
| **US FCT** | `DATASET/INDB/US_fct.xlsx` | 54 | USDA reference foods adapted for South Asian diaspora dietary staples |
| **ICMR-NIN 2017** | `DATASET/INDB/INDB.xlsx` (Food Composition) | 71 | Essential Indian staples (raw grains, pulses, millets, spices, oils) |
| **Volumetric Units** | `DATASET/INDB/Units.xlsx` | 282 | Laboratory-measured food density and volume-to-gram conversions |

**Total Verified Database Foods:** **1,283 items**  
**Total Food-Specific Volume Conversions:** **282 rules**

---

## 2. Ingestion Pipeline Execution

The ingestion pipeline is located at `backend/app/services/ingestion/indb_pipeline.py`.

```mermaid
graph LR
    A[Excel Spreadsheets in DATASET/INDB/] --> B[pandas Data Cleaner & Normalizer]
    B --> C[Column Mapping to Unified Schema]
    C --> D[Food & FoodUnitConversion DB Entities]
    D --> E[(SQLite / PostgreSQL Database)]
```

### Running the Pipeline Manually
```powershell
# From project backend directory
cd backend
.venv\Scripts\python.exe -m app.services.ingestion.indb_pipeline
```

---

## 3. Food-Specific Volumetric Conversion Logic

### 3.1 The Problem with Universal Hard-Coded Grams
In typical generic calorie trackers, 1 "cup" is blindly converted to 240g regardless of the food. In Indian cuisine:
- **1 cup of cooked Dal Tadka** $\approx 240\text{g}$
- **1 cup of cooked Basmati Rice** $\approx 150\text{g}$
- **1 cup of Puffed Rice (Murmura)** $\approx 25\text{g}$
- **1 cup of Raw Spinach / Palak** $\approx 30\text{g}$
- **1 cup of Paneer Cubes** $\approx 150\text{g}$
- **1 cup of Curd / Dahi** $\approx 200\text{g}$

Assuming 240g for 1 cup of puffed rice would overestimate calories by **nearly 1000%**!

### 3.2 Conversion Resolution Algorithm
When a user logs a food with quantity $Q$ and unit $U$:
1. **Direct Mass Units** (`g`, `kg`, `mg`, `oz`, `lb`): Converted directly to grams with confidence = `1.0`.
2. **Serving Unit Match**: If unit matches the item's standard serving unit in INDB (e.g. `piece`, `roti`, `idli`, `slice`), the database standard weight is multiplied by $Q$ with confidence = `1.0`.
3. **Database Food-Specific Density**: `FoodUnitConversion` table is queried for the exact food name and unit. If matched, uses the exact laboratory gram weight with confidence = `0.95`.
4. **Staple Density Fallback**: Matches canonical Indian staple category densities (e.g. `cooked rice` = 150g/cup, `dal` = 240g/cup, `curd` = 200g/cup) with confidence = `0.90`.
5. **Broad Food Category Fallback**: If no food-specific entry is found, matches the category (e.g. generic soup = 240g, generic leaf vegetable = 50g) with confidence = `0.70`.
6. **Generic Universal Fallback**: If all else fails, a generic liquid/solid approximation is used ($1\text{ cup} = 200\text{g}$, $1\text{ tbsp} = 15\text{g}$, $1\text{ tsp} = 5\text{g}$) and **confidence is strictly degraded to $\le 0.65$**.

### 3.3 Uncertainty Engine Flagging
Whenever confidence is degraded to $\le 0.65$:
- `confidence_score` is attached to the meal item record.
- The UI displays an advisory badge: *"Generic portion fallback (60% conf)"*.
- The `generate_clarification_tool` triggers interactive portion choices (e.g. "1 small katori (100g)", "1 medium bowl (150g)", "1 large bowl (225g)").
