# Distributed Microservices Hackathon Project (IUT Cafeteria Crisis System)

A distributed microservices system designed to replace a failing monolith for the IUT Cafeteria. This system handles high-concurrency order placement, real-time stock management, kitchen processing simulation, and instant notifications.

## 1️⃣ Basic README Sections

### Features Overview
- **Identity Provider**: Secure JWT authentication with Redis-backed rate limiting.
- **Order Gateway**: High-throughput entry point with idempotency and caching.
- **Stock Service**: Optimistic locking for inventory management.
- **Kitchen Service**: Asynchronous order processing simulation.
- **Notification Service**: Real-time updates via WebSockets.
- **Frontend**: Student UI for ordering and Admin Dashboard for monitoring.

### Tech Stack
- **Backend**: Python (FastAPI), SQLAlchemy, Pydantic
- **Frontend**: React (Vite), Tailwind CSS
- **Databases**: PostgreSQL (Service-isolated schemas)
- **Caching**: Redis
- **Message Broker**: RabbitMQ
- **Infrastructure**: Docker, Docker Compose, Nginx

### How to Run
The entire system can be started with a single command:

```bash
docker compose up --build
```

Access the application at:
- **Student UI**: http://localhost:3000
- **Admin Dashboard**: http://localhost:3000/admin

### Environment Variables
Environment variables are managed via `docker-compose.yml` and `.env` files. Key variables include:
- `DATABASE_URL`: Connection string for PostgreSQL.
- `REDIS_URL`: Connection string for Redis.
- `RABBITMQ_URL`: Connection string for RabbitMQ.
- `JWT_SECRET`: Secret key for token generation.

### CI/CD Overview
The project uses GitHub Actions for Continuous Integration. The pipeline runs unit tests for all services on every push to `main` and `development` branches.

### Folder Structure
```
.
├── backend/
│   ├── identity-provider/   # Auth & Rate Limiting
│   ├── order-gateway/       # Order Entry & Idempotency
│   ├── stock-service/       # Inventory & Optimistic Locking
│   ├── kitchen-service/     # Order Processing Simulation
│   └── notification-service/# WebSocket Notifications
├── frontend/                # React UI (Student + Admin)
├── .github/workflows/       # CI/CD Pipelines
└── docker-compose.yml       # Orchestration
```

---

## 2️⃣ Ports Table

| Service | Host Port | Internal Port |
| :--- | :--- | :--- |
| **Frontend** | 3000 | 3000 |
| **Order Gateway** | 8000 | 8000 |
| **Identity Provider** | 8001 | 8000 |
| **Stock Service** | 8002 | 8000 |
| **Kitchen Service** | 8003 | 8000 |
| **Notification Service** | 8004 | 8000 |
| **PostgreSQL** | 5433 | 5432 |
| **Redis** | 6379 | 6379 |
| **RabbitMQ** | 5672, 15672 | 5672, 15672 |

---

## 3️⃣ System Architecture

The system follows a microservices architecture with event-driven communication.

### 1. Identity Provider
- **Responsibilities**: User authentication, JWT issuance, Rate Limiting.
- **Key Logic**: Implements a fixed-window rate limiter using Redis.
- **File**: [rate_limit.py](backend/identity-provider/app/rate_limit.py)

```python
# backend/identity-provider/app/rate_limit.py

def is_rate_limited(student_id: str) -> bool:
    """
    Increment the per-student fixed-window login attempt counter.
    """
    key = f"{_KEY_PREFIX}:{student_id}"
    # ... (Redis INCR and EXPIRE logic)
    pipe.incr(key)
    pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS, nx=True)
    # ...
    return attempt_count > settings.RATE_LIMIT_MAX_ATTEMPTS
```

### 2. Order Gateway
- **Responsibilities**: Order validation, Idempotency check, Stock reservation (cache), Event publishing.
- **Key Logic**: Uses the **Outbox Pattern** to reliably publish events to RabbitMQ.
- **File**: [order.py](backend/order-gateway/app/routers/order.py)

```python
# backend/order-gateway/app/routers/order.py

@router.post("/order", ...)
async def place_order(...):
    # Idempotency check
    with _short_session(db_factory) as db:
        existing_key = db.query(IdempotencyKey).filter(...).first()
        if existing_key:
            # Return cached response or error
            pass
    
    # ... Token validation and Order placement logic
```

### 3. Stock Service
- **Responsibilities**: Inventory management, Atomic stock deduction.
- **Key Logic**: Uses **Optimistic Locking** to handle concurrent stock updates.
- **File**: [stock.py](backend/stock-service/app/services/stock.py)

```python
# backend/stock-service/app/services/stock.py

# Attempt update with version check
update_result = (
    db.query(Inventory)
    .filter(
        Inventory.item_id == request.item_id,
        Inventory.version == current_version,
    )
    .update(
        {
            "quantity": Inventory.quantity - request.quantity,
            "version": Inventory.version + 1,
        },
        synchronize_session=False,
    )
)
```

### 4. Kitchen Service
- **Responsibilities**: Order processing simulation.
- **Key Logic**: Simulates cooking time (3-7s) and updates status via RabbitMQ.
- **File**: [processor.py](backend/kitchen-service/app/services/processor.py)

```python
# backend/kitchen-service/app/services/processor.py

async def process_order_background(order_record: dict) -> None:
    """Simulate 3-7 s cooking time, cycling through QUEUED → IN_KITCHEN → READY."""
    cook_time = random.uniform(3.0, 7.0)
    # ... Update status and notify via RabbitMQ
```

### 5. Notification Service
- **Responsibilities**: Consuming events, Persisting notifications, WebSocket push.
- **Key Logic**: Consumes `kitchen_events` and pushes to frontend.
- **File**: [consumer.py](backend/notification-service/app/services/consumer.py)

```python
# backend/notification-service/app/services/consumer.py

async def _on_message(message: AbstractIncomingMessage) -> None:
    # ...
    # Persist to DB
    # Push to student's WebSocket connections
    ws_message = json.dumps({
        "event": "order_status",
        "payload": { ... }
    })
    await send_to_student(student_id, ws_message)
```

---

## 4️⃣ Core Engineering Requirements

- **Microservice Isolation**: Each service runs in its own Docker container with independent dependencies.
- **Independent Databases**: PostgreSQL is used with separate logical databases/schemas for each service to ensure loose coupling.
- **Idempotency**: The Order Gateway uses an `idempotency_keys` table to prevent duplicate order processing.
- **Observability**: All services expose `/health` and `/metrics` endpoints.
- **Fault Tolerance**: 
    - **Rate Limiting**: Fail-open policy if Redis is unavailable.
    - **Message Queues**: RabbitMQ ensures reliable communication between services.
- **Graceful Degradation**: Frontend handles service unavailability with error messages.
- **Chaos Engineering**: The Stock Service includes a `/chaos/kill` endpoint to simulate failure.
- **CI/CD Pipeline**: GitHub Actions runs tests for all services on every commit.

---

## 5️⃣ Bonus Challenges

### Visual Alerts
The Admin Dashboard tracks the **Order Gateway's** average latency. A 30-second rolling average is calculated, and if it exceeds **1 second (1000ms)**, a visual alert is triggered.

**Alert Logic (Frontend):**
```jsx
// frontend/src/components/admin/MetricsPanel.jsx

const GatewayAlertBanner = ({ gatewayUrl }) => {
  const { metrics } = useMetricsPolling(gatewayUrl);
  
  // Alert condition
  if (!metrics?.latency_alert) return null;

  return (
    <div className="mb-6 flex items-start gap-3 rounded-lg border border-red-400 bg-red-50 ...">
      {/* ... Alert UI ... */}
      <p>
        30-second rolling average is{' '}
        <span className="font-mono font-semibold">
          {metrics.rolling_window_avg_ms?.toFixed(0)} ms
        </span>
        {' '}— exceeds the 1 000 ms threshold.
      </p>
    </div>
  );
};
```

### Rate Limiting
The Identity Provider limits login attempts to prevent brute-force attacks. It uses a **Fixed Window** algorithm backed by Redis.

**Enforcement Logic:**
```python
# backend/identity-provider/app/rate_limit.py

def is_rate_limited(student_id: str) -> bool:
    key = f"{_KEY_PREFIX}:{student_id}"
    try:
        client = get_redis_client()
        pipe = client.pipeline()
        pipe.incr(key)
        # Set expiry only on first attempt
        pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS, nx=True)
        results = pipe.execute()
        
        attempt_count: int = results[0]
        return attempt_count > settings.RATE_LIMIT_MAX_ATTEMPTS
    except redis_lib.RedisError:
        # Fail open
        return False
```
**Behavior**: If the limit is exceeded, the API returns a `429 Too Many Requests` status.

---

## 6️⃣ DevOps & Deployment

- **Docker Architecture**: Services are containerized using `Dockerfile`s based on `python:3.11-slim` (Backend) and `node:20` (Frontend).
- **Network**: All services communicate within the `cafeteria-net` bridge network.
- **CI/CD**: GitHub Actions workflow (`.github/workflows/ci.yml`) runs `pytest` for each backend service in parallel.
- **Testing Strategy**: 
    - Unit tests for core logic.
    - Integration tests for API endpoints.
    - CI ensures tests pass before merging.

---

## 7️⃣ Monitoring & Chaos Engineering

- **Admin Dashboard**: Provides real-time visibility into service health and metrics.
- **Health Polling**: The frontend periodically polls `/health` endpoints of all services.
- **Metrics Polling**: Latency and request counts are polled from `/metrics`.
- **Chaos Endpoint**: The **Stock Service** exposes a `/chaos/kill` endpoint.
    - **Action**: Sending a POST request to this endpoint terminates the service process.
    - **Observation**: The Admin Dashboard will show the Stock Service as "Down" until Docker restarts it (or it is manually restarted), demonstrating the system's resilience and monitoring capabilities.
