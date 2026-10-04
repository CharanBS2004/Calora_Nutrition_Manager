# Environment Variables Reference

---

## 1. Backend Service Configuration (`backend/.env`)

| Variable Name | Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | String | `sqlite:///./nutrition_dev.db` | SQLAlchemy connection URI (`postgresql://...` or `sqlite://...`). |
| `ENVIRONMENT` | String | `development` | Runtime environment (`development`, `staging`, `production`). |
| `PORT` | Integer | `8000` | Port on which FastAPI / Uvicorn server binds. |
| `JWT_SECRET_KEY` | String | *Required in production* | Secret key for signing HS256 authentication tokens. |
| `JWT_ALGORITHM` | String | `HS256` | Cryptographic algorithm for JWT generation. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Integer | `60` | Lifespan of JWT bearer access tokens in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Integer | `30` | Lifespan of JWT refresh tokens in days. |
| `GEMINI_API_KEY` | String | Optional (Fallback to offline rules) | Google Gemini API key for natural language agent and transcription. |
| `INDB_DATA_DIR` | String | `../DATASET/INDB` | Filesystem path pointing to the INDB Excel files directory. |

---

## 2. Docker Compose Environment (`docker/.env` or Compose variables)

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `POSTGRES_USER` | `postgres` | Database superuser username. |
| `POSTGRES_PASSWORD` | `postgres` | Database superuser password. |
| `POSTGRES_DB` | `nutrition_db` | Primary relational database name. |

---

## 3. Mobile Client Configuration (`mobile/lib/core/constants/api_constants.dart`)

| Constant Name | Default Value | Description |
| :--- | :--- | :--- |
| `defaultBaseUrl` | `http://10.0.2.2:8000/api/v1` | Root API base URL for REST requests. Set to LAN IP for physical device. |
