# Local Development & Environment Setup Guide

---

## 1. Prerequisites

Ensure you have the following installed on your system:
- **Python 3.11+**
- **Flutter SDK 3.22+** (with Android SDK 34 / Android Studio)
- **Git**
- *(Optional)* **Docker & Docker Compose** for containerized deployment

---

## 2. Backend Setup (FastAPI & Python)

### 2.1 Navigate and Create Virtual Environment
```powershell
# Open terminal in project root
cd "E:\BMSCE\3rd Sem\AAI\Nutrition_Manager\backend"

# Create virtual environment if not already present
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

### 2.2 Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2.3 Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure `.env` contains:
```env
DATABASE_URL=sqlite:///./nutrition_dev.db
JWT_SECRET_KEY=nutrition-super-secret-jwt-key-for-development-change-in-prod-2026
ENVIRONMENT=development
PORT=8000
```

### 2.4 Run Database Ingestion Pipeline
To load all 1,283 verified foods and 282 Units conversions from the INDB dataset:
```powershell
python -m app.services.ingestion.indb_pipeline
```

### 2.5 Run Backend Development Server
```powershell
python run.py
```
The FastAPI backend will start at: `http://localhost:8000`  
Interactive Swagger API documentation: `http://localhost:8000/docs`

---

## 3. Running Automated Tests

Run the complete test suite with verbose reporting:
```powershell
cd "E:\BMSCE\3rd Sem\AAI\Nutrition_Manager\backend"
.venv\Scripts\pytest.exe -v
```
All 19 tests across unit conversion, nutrition calculation, reflection node, proactive notifications, and user isolation will execute.

---

## 4. Mobile Frontend Setup (Flutter / Android)

### 4.1 Navigate to Mobile Directory
```powershell
cd "E:\BMSCE\3rd Sem\AAI\Nutrition_Manager\mobile"
```

### 4.2 Fetch Flutter Packages
```bash
flutter pub get
```

### 4.3 Configure Target API Endpoint
The default base URL in `mobile/lib/core/constants/api_constants.dart` is set to:
```dart
static const String defaultBaseUrl = "http://10.0.2.2:8000/api/v1";
```
- **Android Emulator**: `10.0.2.2` routes automatically to your host machine's `localhost`.
- **Physical Android Device**: Change `10.0.2.2` to your computer's local Wi-Fi IP address (e.g. `192.168.1.15`).

### 4.4 Launch the App
```bash
# Connect Android device or launch Android emulator, then run:
flutter run
```
