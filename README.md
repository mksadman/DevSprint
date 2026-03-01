# DevSprint — IUT Cafeteria Crisis System

A microservices-based cafeteria ordering platform with a FastAPI backend, RabbitMQ event bus, and a React frontend.

---

## Project Structure

```
DevSprint/
├── backend/
│   ├── identity-provider/         # JWT auth — login, register, /me
│   ├── order-gateway/            # Order entry point — validates, deducts stock, publishes events
│   ├── stock-service/            # Inventory CRUD + stock deduction
│   ├── kitchen-service/          # Consumes order events, tracks kitchen queue
│   └── notification-service/     # WebSocket push + RabbitMQ consumer
├── frontend/                     # React 18 + Vite + Tailwind CSS
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
| PostgreSQL | 16+ (or run via Docker) |
| Redis | 7+ (or run via Docker) |
| RabbitMQ | 3+ (or run via Docker) |

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

```bash
# generic pattern (run from inside the service directory)
cd backend/<service-name>
pip install -r requirements.txt
```

### 4 — Configure environment variables

Each service reads the following variables (set them in your shell or a `.env` file):

```dotenv
DATABASE_URL=postgresql://cafeteria:cafeteria_pass@localhost:5432/cafeteria_db
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
JWT_SECRET=your-secret-key
```

### 5 — Start infrastructure

```bash
docker run -d -p 5433:5432 \
  -e POSTGRES_USER=cafeteria \
  -e POSTGRES_PASSWORD=cafeteria_pass \
  -e POSTGRES_DB=cafeteria_db \
  postgres:16-alpine

docker run -d -p 6379:6379 redis:7-alpine

docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management-alpine
```

### 6 — Run a service

```bash
cd backend/identity-provider
uvicorn app.main:app --reload --port 8001
```

Repeat on the ports listed in the table below. Interactive API docs are available at `http://localhost:<port>/docs`.

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

## Service Ports

| Service | Host port | Internal port |
|---|---|---|
| `order-gateway` | 8000 | 8000 |
| `identity-provider` | 8001 | 8000 |
| `stock-service` | 8002 | 8000 |
| `kitchen-service` | 8003 | 8000 |
| `notification-service` | 8004 | 8000 |
| `frontend` | 3000 | 3000 |
| `postgres` | 5433 | 5432 |
| `redis` | 6379 | 6379 |
| `rabbitmq` | 5672 / 15672 | 5672 / 15672 |

---

## Running Tests

```bash
# example — identity-provider
cd backend/identity-provider
pytest tests/ -v

# example — order-gateway
cd backend/order-gateway
pytest tests/ -v
```

Each service has its own `tests/` (or `test/`) directory.

---

## API Overview

### Identity Provider — port 8001

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/login` | — | Authenticate, returns JWT |
| `POST` | `/register` | — | Register a new student |
| `GET` | `/me` | Bearer | Current user info |
| `GET` | `/health` | — | Liveness probe |
| `GET` | `/metrics` | — | Login counters and latency |

#### POST /login

```json
// Request
{ "student_id": "student001", "password": "password123" }

// 200 OK
{ "access_token": "<jwt>", "token_type": "bearer" }

// 401 Unauthorized
{ "detail": "Invalid student_id or password." }
```

---

### Order Gateway — port 8000

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/order` | Bearer | Place an order (idempotent) |
| `GET` | `/orders` | Bearer | List orders for current student |
| `GET` | `/health` | — | Dependency health check |
| `GET` | `/metrics` | — | Order counters and latency |

---

### Stock Service — port 8002

| Method | Path | Description |
|---|---|---|
| `POST` | `/items` | Create inventory item |
| `GET` | `/items` | List all items |
| `GET` | `/items/{item_id}` | Get item by ID |
| `PUT` | `/items/{item_id}` | Replace item |
| `PATCH` | `/items/{item_id}` | Update item fields |
| `DELETE` | `/items/{item_id}` | Delete item |
| `POST` | `/stock/deduct` | Deduct stock for an order |
| `GET` | `/transactions/{order_id}` | Audit log by order |
| `GET` | `/transactions/` | Full audit log |
| `GET` | `/health` | Liveness probe |
| `GET` | `/metrics` | Deduction counters and latency |

---

### Kitchen Service — port 8003

| Method | Path | Description |
|---|---|---|
| `POST` | `/orders` | Manually enqueue an order |
| `GET` | `/orders/{order_id}/status` | Get kitchen status for an order |
| `GET` | `/health` | Liveness probe |
| `GET` | `/metrics` | Queue counters |

---

### Notification Service — port 8004

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe (RabbitMQ + DB) |
| `GET` | `/metrics` | WebSocket and message counters |
| `POST` | `/notify` | Push a notification to a student |
| `WS` | `/ws` | WebSocket connection for real-time updates |
