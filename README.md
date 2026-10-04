# AI-Powered Personal Nutrition & Energy Balance Coach

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Flutter](https://img.shields.io/badge/Mobile-Flutter%203.22+-02569B.svg?style=flat&logo=flutter)](https://flutter.dev)
[![Android](https://img.shields.io/badge/Platform-Android%20SDK%2034-3DDC84.svg?style=flat&logo=android)](https://developer.android.com)
[![LangGraph](https://img.shields.io/badge/Agent-LangGraph-FF6F00.svg?style=flat)](https://github.com/langchain-ai/langgraph)
[![INDB Grounded](https://img.shields.io/badge/Dataset-INDB%201%2C283%20Foods-success.svg)](#1-indian-nutrient-databank-indb--unitsxlsx-grounding)
[![Tests](https://img.shields.io/badge/Tests-19%2F19%20Passing%20(100%25)-brightgreen.svg)](#8-automated-test-suite)

> An enterprise-grade, mobile-first agentic AI nutrition and energy balance coaching platform specifically tailored for Indian foods, recipes, cooking methods, and volumetric serving units.

> **Dataset notice:** Third-party nutrition tables and recipe workbooks are not included in this repository. Obtain any required datasets from their original sources and comply with their licensing and access terms before placing them in `DATASET/INDB/`.

---

## Key Pillars of the System

```
                      +------------------------------------------+
                      |         Android Flutter Frontend         |
                      |  Material 3 Wellness Theme (Sage & Teal) |
                      | Health Connect Telemetry | WorkManager   |
                      +--------------------+---------------------+
                                           | REST API / JSON
                                           v
                      +--------------------+---------------------+
                      |         FastAPI Backend Engine           |
                      |  Strict User Isolation | JWT Security    |
                      +--------------------+---------------------+
                                           |
         +---------------------------------+---------------------------------+
         |                                                                   |
         v                                                                   v
+-----------------------+                                         +-----------------------+
|  Deterministic Layer  |                                         |   Agentic AI Layer    |
| - INDB Food Database  |                                         | - LangGraph Graph     |
|   (1,283 items)       |                                         | - 20 Distinct Tools   |
| - Units.xlsx Volume   | <-------------------------------------- | - Post-Action         |
|   Densities (282 rules)|                                        |   Reflection Node     |
| - Zero-LLM Arithmetic |                                         | - Uncertainty Engine  |
| - Method C Recipes    |                                         | - Safety Guardrails   |
+-----------------------+                                         +-----------------------+
```

---

## 1. Core Feature Highlights

### 1. Indian Nutrient Databank (INDB) & Units.xlsx Grounding
- **1,283 verified laboratory items**: 1,014 INDB authentic Indian recipes, 144 UK FCT items, 54 US FCT items, and 71 ICMR-NIN 2017 essential staples.
- **282 Food-Specific Volume Conversions**: Grounded in laboratory measurements from `Units.xlsx` (e.g. 1 cup cooked dal = 240g, 1 cup cooked rice = 150g, 1 cup puffed rice = 25g). **No blind 240g hardcoded conversions**. Fallbacks are strictly tagged with confidence $\le 0.65$.

### 2. Zero-Hallucination Deterministic Engine
- **LLMs are strictly forbidden from performing nutrition arithmetic**.
- Natural language meal descriptions and voice transcripts are parsed into candidate items, resolved against INDB, and calculated using deterministic Python formulas ($O(1)$ lookup guarantees).

### 3. Method C Recipe Builder
- Interactive ingredient builder calculating raw-to-cooked yield, total recipe macros, per-serving values, and per-100g cooked values.
- 1-tap saving to personal recipe library and direct meal logging.

### 4. LangGraph Multi-Turn Agent & Post-Action Reflection Node
- Stateful computational graph equipped with **20 deterministic tools**.
- **Post-Action Reflection Node**: Validates macro outputs ($0 \le \text{cal} \le 5000$), verifies consistency ($(4P + 4C + 9F) \approx \text{kcal}$), tracks remaining goals, evaluates uncertainty level, and returns structured action buttons.

### 5. Nutrition Safety Guardrails & Uncertainty Engine
- **Medical Disclaimer**: Emphasizes educational and coaching nature; strictly blocks medical diagnosis or prescription.
- **Eating Disorder & Starvation Safeguards**: Rejects extreme deficits ($< 1200 \text{ kcal}$ for females, $< 1500 \text{ kcal}$ for males).
- **Uncertainty Clarification**: When portion confidence $< 0.70$, surfaces multiple-choice portion options for human-in-the-loop confirmation.

### 6. Android Health Connect & Energy Balance
- Direct integration with Android Health Connect to ingest steps, active calories, and total energy expenditure.
- Computes daily **Calories In vs Calories Out** ($E_{\text{balance}} = C_{\text{in}} - C_{\text{out}}$) and classifies status into *Deficit*, *Surplus*, or *Maintenance*.

### 7. Proactive Background Notifications & Quiet Hours
- Scheduled meal check-ins via native Android `WorkManager` (periodic wakeups every 15-30 minutes).
- Respects user-configurable quiet hours (e.g. 22:00 to 07:00) and meal schedules (Breakfast, Lunch, Dinner, Snack).

### 8. Pluggable Speech-to-Text (STT) Abstraction
- Dual-mode architecture supporting Google Cloud STT with automatic fallback to on-device Android `SpeechRecognizer`.

### 9. Material 3 Wellness Design System
- Calming natural palette: Sage (`#3F7D5A`), Deep Teal (`#2F6547`), Cream (`#F7F8F3`), and Dark Slate (`#0D1410`).
- Semantic macro colors: Protein (Blue), Carbs (Amber), Fat (Coral), Fiber (Emerald).
- Smooth responsive transitions across phone and tablet form factors.

---

## 2. Directory Structure

```
Nutrition_Manager/
├── backend/                  # Python FastAPI Backend
│   ├── app/
│   │   ├── api/v1/           # REST endpoints (auth, meals, recipes, health, agent, analytics)
│   │   ├── core/             # Database session, config, security, auth deps
│   │   ├── models/           # SQLAlchemy entity models with user isolation
│   │   ├── schemas/          # Pydantic v2 request & response schemas
│   │   └── services/
│   │       ├── agent/        # LangGraph orchestrator, reflection node, 20 tools, safety
│   │       ├── ingestion/    # INDB Excel ingestion pipeline (1,283 foods, 282 conversions)
│   │       ├── memory/       # Short-term and long-term user memory service
│   │       ├── nutrition_engine.py  # Deterministic formulas (zero LLM arithmetic)
│   │       ├── unit_converter.py    # Food-specific density resolution & fallbacks
│   │       └── analytics_service.py # Daily, weekly, monthly reports & comparisons
│   ├── tests/                # 19 automated pytest test suites
│   ├── requirements.txt      # Frozen backend dependencies
│   └── run.py                # Server runner
├── mobile/                   # Android Flutter Mobile Application
│   ├── android/              # Native Android manifests, Health Connect permissions, Gradle
│   ├── lib/
│   │   ├── core/             # Theme, network client, STT service, Health Connect, WorkManager
│   │   ├── models/           # Dart data models matching backend schemas
│   │   ├── providers/        # State management (Theme, Auth, Nutrition, Coach)
│   │   └── ui/
│   │       ├── screens/      # Home, LogFood, RecipeBuilder, RecipeLibrary, Analytics, Coach, Profile, Auth
│   │       └── widgets/      # CalorieHeroRing, MacroProgressBar, EnergyBalanceCard, MealStatusTile
│   └── pubspec.yaml          # Flutter package dependencies
├── DATASET/
│   └── INDB/                 # Add separately obtained, authorized data files here
├── docker/                   # Containerization
│   ├── Dockerfile            # Multi-stage production build for FastAPI backend
│   └── docker-compose.yml    # PostgreSQL 16 + pgvector and FastAPI backend services
└── docs/                     # Comprehensive Project Documentation
    ├── ARCHITECTURE.md       # Detailed system architecture & invariant separation
    ├── AI_AGENT.md           # LangGraph state machine, reflection node & 20 tools
    ├── DATA_PIPELINE.md      # INDB dataset ingestion & volume density resolution
    ├── HEALTH_CONNECT.md     # Health Connect permissions, telemetry & energy balance
    ├── DATABASE_SCHEMA.md    # Normalized ER diagram, tables & vector embeddings
    ├── API_DOCUMENTATION.md  # Complete REST API reference with schemas
    ├── SETUP.md              # Local development setup & execution guide
    ├── DEPLOYMENT.md         # Production deployment & Docker operations
    ├── ENVIRONMENT_VARIABLES.md # Environment variables reference
    └── TESTING.md            # Testing strategy & automated test suite breakdown
```

---

## 3. Quick Start Guide

### 3.1 Backend Setup
```powershell
# Navigate to backend
cd backend

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Start the development server
python run.py
```
Backend runs at: `http://localhost:8000` (Swagger UI: `http://localhost:8000/docs`).

### 3.2 Run Automated Tests
```powershell
cd backend
.venv\Scripts\pytest.exe -v
```
**Output:**
```
============================== 19 passed in 4.72s ==============================
```

### 3.3 Launch Mobile Application
```bash
cd mobile
flutter pub get
flutter run
```

### 3.4 Containerized Deployment with Docker
```bash
docker-compose -f docker/docker-compose.yml up -d --build
```

---

## 4. Documentation Index

For detailed engineering guides, refer to the documentation suite in [`docs/`](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs):
- [Architecture & Invariants](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/ARCHITECTURE.md)
- [LangGraph Agent & 20 Tools](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/AI_AGENT.md)
- [INDB & Units.xlsx Data Pipeline](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/DATA_PIPELINE.md)
- [Android Health Connect & Energy Balance](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/HEALTH_CONNECT.md)
- [Database Schema & ER Model](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/DATABASE_SCHEMA.md)
- [REST API Reference](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/API_DOCUMENTATION.md)
- [Environment Variables](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/ENVIRONMENT_VARIABLES.md)
- [Local Setup Guide](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/SETUP.md)
- [Production Deployment](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/DEPLOYMENT.md)
- [Testing Strategy](file:///E:/BMSCE/3rd%20Sem/AAI/Nutrition_Manager/docs/TESTING.md)

---

## 5. Verification & Quality Assurance

- **100% Automated Backend Test Coverage**: 19 out of 19 tests passing across auth, isolation, reflection, proactive notifications, analytics, health balance, and volume conversions.
- **Strict User Isolation**: Foreign key ownership validation across all endpoints.
- **Deterministic Math Invariant**: All nutritional totals, macro targets, and energy balance computations are verified against laboratory compositions.
