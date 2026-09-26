# DrillLens

Powered by eRTMAC-NWIS

Enhanced Real-Time Monitoring & Control Centre – Nearby Well Intelligence System

DrillLens is an engineering intelligence and decision-support application. It connects the current drilling condition, nearby wells, historical events, similarity, risk indicators, and source evidence.

It does **not** control drilling equipment, change drilling parameters, or authorize operations. Final decisions stay with qualified drilling engineers.

Risk indicators come from a documented rule engine (`docs/RISK_RULES.md`). There is no trained machine-learning model in this deployment, and the interface does not display an accuracy percentage.

## Architecture

- React, TypeScript, Tailwind, Chart.js, Leaflet
- FastAPI, SQLAlchemy, Alembic, JWT, WebSocket
- PostgreSQL with PostGIS geography points
- PyMuPDF text extraction and Tesseract OCR for low-text PDF pages
- Regex, rules, and spaCy when `en_core_web_sm` is installed
- Nginx serves the frontend and proxies `/api` and `/ws`

The live parameter feed is a **DEMO SENSOR STREAM** (`SimulatedSensorAdapter`). Replace it by implementing `SensorAdapter` and setting `SENSOR_ADAPTER`. Do not present simulated values as rig measurements; the UI labels them `SIMULATED`.

## Setup

```bash
cd drilllens
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080). API docs: [http://localhost:8080/docs](http://localhost:8080/docs) and [http://localhost:8080/redoc](http://localhost:8080/redoc).

The backend container runs `alembic upgrade head` and `scripts/seed_database.py` before Uvicorn starts. PostgreSQL data and uploads are stored in Docker volumes.

## Environment variables

Copy `.env.example` to `.env`. The compose file already supplies local development values. Change every secret before any shared or production deployment.

| Variable | Purpose |
| --- | --- |
| DATABASE_URL | SQLAlchemy PostgreSQL URL |
| SECRET_KEY | Application secret |
| JWT_SECRET_KEY | JWT signing key |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | Access token lifetime |
| UPLOAD_DIRECTORY | Report storage root |
| MAX_UPLOAD_SIZE_MB | Upload limit |
| TESSERACT_PATH | Tesseract binary |
| OCR_LANGUAGE | Tesseract language |
| CORS_ORIGINS | Allowed browser origins |
| WEBSOCKET_INTERVAL_SECONDS | Demo sensor interval |
| OSM_TILE_URL | Leaflet tile template |
| ENVIRONMENT | `development` enables extra diagnostics |
| RETURN_RESET_TOKEN | Development only. Must be false when real email delivery exists |
| SENSOR_ADAPTER | `simulated` until a rig adapter is registered |
| RISK_ENGINE | `rule_based` |
| ENABLE_SPACY | Load spaCy if the model is present |
| ENABLE_TRANSFORMERS | Must stay false until a validated model is registered |

The frontend never receives `SECRET_KEY` or `JWT_SECRET_KEY`. It only reads a public config endpoint for the map tile URL and product name.

## Development accounts

These accounts are created by the seed script for local development only. Replace them before production.

| Role | Username | Password |
| --- | --- | --- |
| Admin | admin | Admin123! |
| Drilling engineer | engineer | Engineer123! |
| Viewer | viewer | Viewer123! |

## Database and migrations

PostGIS is enabled by Alembic revision `0001_initial`. Well coordinates use `GEOGRAPHY(Point, 4326)`. Nearby search uses `ST_DWithin` and `ST_Distance` in the database, not in the browser.

```bash
docker compose exec backend alembic upgrade head
```

## Seed data

`scripts/seed_database.py` loads eight DEMO wells around a fictional North Rift cluster, formations, trajectories, parameter history, drilling events, evidence, one engineering review, and `scripts/WCR_DEMO_001.txt`. Seeded analytical rows use `source_type = DEMO` where that field exists. The script does nothing if users already exist.

## OCR and Tesseract

Normal PDFs are read with PyMuPDF. A page with very little embedded text is rendered and passed to Tesseract. The original file is kept. OCR text, confidence, and timing are stored on `ocr_results`. If Tesseract is missing, that page is marked failed and no text is invented.

## Search

PostgreSQL full-text search covers wells, reports, events, formations, and evidence. `search_service.py` is the only search entry point so a later Elasticsearch, OpenSearch, or vector index can replace the SQL.

## Testing

Unit tests for extraction, risk rules, and password hashing do not need a database. API tests run when PostGIS is reachable.

```bash
docker compose exec backend pytest
```

Frontend:

```bash
cd frontend
npm install
npm test
npm run build
```

## Security

Passwords are hashed with bcrypt. Sessions are JWTs with a logout denylist. Roles are Admin, Drilling Engineer, and Viewer. Uploads are limited by size and extension, stored under a generated name, and never executed. Queries use SQLAlchemy or bound parameters. Audit logs record sign-in, uploads, well changes, reviews, alert actions, and configuration changes. Passwords and tokens are not written to the audit metadata.

## Known limitations

- The sensor feed is simulated and labeled as such.
- Password reset returns the token only when `RETURN_RESET_TOKEN=true` in development. Production needs an email delivery service and that flag set to false.
- No transformer model is bundled. `ENABLE_TRANSFORMERS` does not load weights.
- spaCy is optional. Rules still extract the demo report if the model download fails.
- Object storage is not wired. Files stay on the local upload volume behind `assert_inside`.
- One backend process owns the in-memory WebSocket hub and demo sensor loop.
