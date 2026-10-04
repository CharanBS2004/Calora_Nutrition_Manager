# Production Deployment & Operations Guide

---

## 1. Containerized Deployment with Docker Compose

The production deployment runs the FastAPI backend behind uvicorn with a dedicated PostgreSQL 16 database equipped with the `pgvector` extension.

### 1.1 Configuration Checklist
1. Navigate to the `docker/` directory or project root.
2. Ensure you have configured environment secrets in `.env`:
   ```env
   POSTGRES_USER=nutrition_admin
   POSTGRES_PASSWORD=UltraSecurePassword2026!
   POSTGRES_DB=nutrition_production_db
   JWT_SECRET_KEY=production-crypto-random-secret-key-minimum-32-chars
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### 1.2 Build & Launch Services
```bash
# In the project root or docker directory
docker-compose -f docker/docker-compose.yml up -d --build
```

### 1.3 Verify Health Status
```bash
docker ps
# Inspect container health:
docker inspect --format='{{json .State.Health}}' nutrition_backend
```

---

## 2. Reverse Proxy & SSL Configuration (Nginx / Cloudflare)

For production web and mobile traffic, terminate TLS using Nginx or Cloudflare:

```nginx
server {
    listen 443 ssl http2;
    server_name api.nutritioncoach.app;

    ssl_certificate /etc/letsencrypt/live/api.nutritioncoach.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.nutritioncoach.app/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 3. Database Migration & Maintenance

When deploying updates:
```bash
# Run Alembic migrations inside container
docker exec -it nutrition_backend alembic upgrade head

# Backup database
docker exec -t nutrition_postgres pg_dump -U postgres nutrition_db > backup_$(date +%F).sql
```

---

## 4. Mobile Production Release (Android APK / AAB)

To produce release artifacts for the Google Play Store:
```bash
cd mobile

# Generate signed Android App Bundle (AAB)
flutter build appbundle --release

# Generate standalone APK for sideloading/testing
flutter build apk --release
```
The output will be placed in `mobile/build/app/outputs/bundle/release/app-release.aab`.
