# DevSprint 2026 – Distributed Database Architecture

## Microservices-Based Design (DevOps-Oriented)

This document defines:

- Database schema for all 5 services
- Table structures with foreign keys (within each service only)
- Industry / competition-grade constraints followed
- Complete system flow
- How cross-service integrity is ensured at the application level (not DB level)

---

# Architectural Principles Followed

1. Each service owns its database.
2. No cross-service foreign keys.
3. Strong consistency inside a service.
4. Eventual consistency across services.
5. UUID-based global identifiers.
6. DevOps-ready design (auditability, observability, retry safety).

---

# 1️⃣ Identity Provider Database

## Responsibility
- Authentication
- JWT issuance
- Rate limiting
- Login metrics

## Tables

### users

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | Internal unique ID |
| student_id | VARCHAR | UNIQUE, NOT NULL | Public student identifier |
| password_hash | TEXT | NOT NULL | Secure hashed password |
| created_at | TIMESTAMP | NOT NULL | Creation time |
| updated_at | TIMESTAMP | NOT NULL | Update time |

### login_attempts

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | Attempt ID |
| user_id | UUID | FK → users.id | Related user |
| attempted_at | TIMESTAMP | NOT NULL | Attempt time |
| success | BOOLEAN | NOT NULL | Success flag |
| response_time_ms | INT | NOT NULL | Latency tracking |

## Relationships

- users (1) → (N) login_attempts

## Industry Practices Followed

- Password hashing
- Audit logging
- Metrics-ready schema
- Rate limiting support
- No cross-service DB coupling

---

# 2️⃣ Order Gateway Database

## Responsibility
- Order initialization
- Idempotency protection
- Request safety

## Tables

### orders

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | Global order ID |
| student_id | VARCHAR | NOT NULL | Authenticated user reference |
| status | VARCHAR | NOT NULL | Order state |
| created_at | TIMESTAMP | NOT NULL | Created time |
| updated_at | TIMESTAMP | NOT NULL | Status update time |

### idempotency_keys

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | Record ID |
| order_id | UUID | FK → orders.id | Linked order |
| key | VARCHAR | UNIQUE, NOT NULL | Idempotency key |
| response_snapshot | JSONB | NOT NULL | Stored response |
| created_at | TIMESTAMP | NOT NULL | Created time |

## Relationships

- orders (1) → (1) idempotency_keys

## Industry Practices Followed

- Stripe-style idempotency pattern
- Retry-safe API design
- Distributed UUID identifiers
- Failure resilience
- Application-level transaction coordination

---

# 3️⃣ Stock Service Database

## Responsibility
- Inventory source of truth
- Concurrency control
- Prevent overselling

## Tables

### items

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | Item ID |
| name | VARCHAR | NOT NULL | Item name |
| price | DECIMAL | NOT NULL | Item price |
| created_at | TIMESTAMP | NOT NULL | Created time |

### inventory

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | Inventory ID |
| item_id | UUID | FK → items.id, UNIQUE | One-to-one relation |
| quantity | INT | CHECK (quantity >= 0) | Stock count |
| version | INT | NOT NULL | Optimistic locking version |
| updated_at | TIMESTAMP | NOT NULL | Updated time |

### stock_transactions

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | Transaction ID |
| order_id | UUID | NOT NULL | Related order (logical reference) |
| item_id | UUID | FK → items.id | Item reference |
| quantity_deducted | INT | NOT NULL | Deducted amount |
| created_at | TIMESTAMP | NOT NULL | Timestamp |

## Relationships

- items (1) → (1) inventory
- items (1) → (N) stock_transactions

## Industry / Competition Constraints

- Optimistic locking (version column)
- CHECK constraint prevents negative inventory
- Transaction logging for auditing
- Logical order reference (no cross-service FK)
- Concurrency-safe design

---

# 4️⃣ Kitchen Service Database

## Responsibility
- Asynchronous processing
- Order lifecycle tracking

## Tables

### kitchen_orders

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | Kitchen record ID |
| order_id | UUID | NOT NULL | Gateway order reference |
| status | VARCHAR | NOT NULL | Current state |
| received_at | TIMESTAMP | NOT NULL | Received time |
| started_at | TIMESTAMP | NULL | Cooking start |
| completed_at | TIMESTAMP | NULL | Cooking finish |

### order_status_history

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | History ID |
| kitchen_order_id | UUID | FK → kitchen_orders.id | Related order |
| status | VARCHAR | NOT NULL | State |
| changed_at | TIMESTAMP | NOT NULL | Change time |

## Relationships

- kitchen_orders (1) → (N) order_status_history

## Industry Practices

- Full lifecycle tracking
- Event-driven architecture compatibility
- Observability-friendly schema
- Separation of processing and tracking

---

# 5️⃣ Notification Service Database

## Responsibility
- Notification delivery logging
- Audit support

## Tables

### notifications

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| id | UUID | PK | Notification ID |
| order_id | UUID | NOT NULL | Related order (logical reference) |
| student_id | VARCHAR | NOT NULL | Recipient |
| status_sent | VARCHAR | NOT NULL | Delivered status |
| sent_at | TIMESTAMP | NOT NULL | Sent time |

## Industry Practices

- Delivery traceability
- Debug support
- Independent service ownership
- No cross-service foreign keys

---

# 🔄 Complete System Flow

## Step 1 – Authentication
- Student logs in.
- Identity verifies credentials.
- JWT issued.
- Login attempt recorded.

## Step 2 – Order Placement
- Gateway validates JWT signature.
- Idempotency key checked.
- Order created (status = PENDING).

## Step 3 – Stock Verification
- Gateway calls Stock Service.
- Optimistic locking update performed.
- Stock transaction recorded.

## Step 4 – Kitchen Processing (Async)
- Message published to queue.
- Kitchen consumes message.
- Status transitions recorded.
- History table updated.

## Step 5 – Notification
- Notification pushed to client.
- Delivery logged.

---

# 🔐 Why There Are No Foreign Keys Between Services

Foreign keys only work inside a single database.

In this architecture:

- Each service has its own database instance.
- Cross-service joins are impossible by design.
- Services communicate via APIs or message queues.
- Data consistency across services is enforced at the application layer.

This ensures:

- Independent deployment
- Fault isolation
- Scalability
- Clean domain ownership

---

# 🧠 How Cross-Service Integrity Is Ensured (Application-Level)

## 1. JWT-Based Identity Verification
- Gateway verifies cryptographic signature.
- student_id is trusted after token validation.
- No DB join required.

## 2. UUID Global Identifiers
- Gateway generates order_id (UUID).
- Same ID propagated across services.
- Logical linkage via shared identifier.

## 3. Strict API Contracts
- Message payload schemas strictly defined.
- Input validation at service boundary.
- Invalid references rejected immediately.

## 4. Idempotency Protection
- Duplicate requests safely handled.
- Prevents double processing during retries.

## 5. Service Ownership Model

| Domain | Authority |
|--------|-----------|
| Identity | User validity |
| Gateway | Order creation |
| Stock | Inventory truth |
| Kitchen | Cooking state |
| Notification | Delivery state |

Each service is the single source of truth for its domain.

---

# Final Architectural Decision

This system intentionally prioritizes:

- Distributed consistency
- Fault isolation
- Retry safety
- Observability
- Independent scaling

Over:

- Centralized relational coupling

This aligns with modern production-grade distributed systems architecture.