# DevSprint

A microservices-based platform with a FastAPI backend and a frontend client.

---

## Project Structure

```
DevSprint/
├── backend/
│   ├── requirements.txt          # Shared deps for all backend services
│   ├── identity-provider/        # Auth service — JWT login, health, metrics
│   │   ├── requirements.txt
│   │   └── app/
│   ├── order-gateway/            # (coming soon)
│   └── ...                       # 3 more services
├── frontend/
├── docker-compose.yml
└── README.md
```

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.11+ |
| pip | 23+ |
| Docker & Docker Compose | 24+ |
| Redis | 7+ (or run via Docker) |

---

## Local Setup (without Docker)

### 1 — Clone the repo

```bash
git clone <repo-url>
cd DevSprint
```

### 2 — Create and activate a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3 — Install dependencies

Each service inherits the shared root requirements and adds its own on top.

```bash
# identity-provider
cd backend/identity-provider
pip install -r ../requirements.txt -r requirements.txt
```

Repeat the pattern for every other service:

```bash
# generic pattern (run from inside the service directory)
cd backend/<service-name>
pip install -r ../requirements.txt -r requirements.txt
```

### 4 — Configure environment variables

Copy the example env file and fill in your values:

```bash
cp backend/identity-provider/.env.example backend/identity-provider/.env
```

Minimum required variables:

```dotenv
JWT_SECRET=your-secret-key
REDIS_URL=redis://localhost:6379
```

### 5 — Start Redis (if not already running)

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 6 — Run a service

```bash
cd backend/identity-provider
uvicorn app.main:app --reload --port 8001
```

Interactive API docs will be available at `http://localhost:8001/docs`.

---

## Running with Docker Compose

```bash
# Build and start all services
docker compose up --build

# Run in the background
docker compose up --build -d

# Tear down (keep volumes)
docker compose down

# Tear down and remove volumes
docker compose down -v
```

---

## Running Tests

```bash
cd backend/identity-provider
pytest tests/ -v
```

---

## API Overview

### Identity Provider (`/`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/login` | Authenticate student, returns JWT |
| `GET` | `/health` | Liveness probe — checks service + Redis |
| `GET` | `/metrics` | Login counters and average response time |

#### POST /login

```json
// Request
{ "student_id": "student001", "password": "password123" }

// 200 OK
{ "access_token": "<jwt>", "token_type": "bearer" }

// 401 Unauthorized
{ "detail": "Invalid student_id or password." }

// 429 Too Many Requests
{ "detail": "Too many login attempts. Please wait and try again." }
```

#### GET /health

```json
// 200 OK
{ "status": "ok", "redis": "reachable" }

// 503 Service Unavailable
{ "detail": "Redis unreachable: ..." }
```

#### GET /metrics

```json
{
  "total_login_attempts": 42,
  "failed_attempts": 5,
  "rate_limit_blocks": 2,
  "average_response_time_ms": 18.743
}
```
