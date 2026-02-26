# DevSprint 2026  
## Requirement Analysis Document  

---

# 1️⃣ User Requirements  

## 1.1 Student Requirements  

- Students shall log in securely using Student ID and password.  
- Students shall receive a JWT token after successful login.  
- Students shall place an order during peak rush without system freeze.  
- Students shall receive fast acknowledgment (< 2 seconds).  
- Students shall see real-time order status updates.  
- Students shall view order transitions:  
  - Pending  
  - Stock Verified  
  - In Kitchen  
  - Ready  
- Students shall not lose orders due to service failure.  

---

## 1.2 Kitchen Staff Requirements  

- Kitchen shall receive all valid orders reliably.  
- Kitchen processing shall not block user requests.  
- Kitchen shall update order status when cooking progresses.  

---

## 1.3 Admin Requirements  

- Admin shall view health status of each microservice.  
- Admin shall view live metrics (latency, throughput).  
- Admin shall simulate service failure (Chaos Toggle).  
- Admin shall run the full system using a single command.  

---

# 2️⃣ Functional Requirements  

## 2.1 Identity Provider  

- FR-1: The system shall authenticate students.  
- FR-2: The system shall issue a signed JWT on successful login.  
- FR-3: The system shall reject invalid credentials.  
- FR-4: The system shall limit login attempts to 3 per minute per Student ID.  

---

## 2.2 Order Gateway  

- FR-5: The Gateway shall validate JWT tokens.  
- FR-6: The Gateway shall reject unauthorized requests with 401.  
- FR-7: The Gateway shall check cache before calling Stock Service.  
- FR-8: The Gateway shall reject instantly if stock is zero.  
- FR-9: The Gateway shall support idempotent order requests.  
- FR-10: The Gateway shall acknowledge valid orders quickly.  

---

## 2.3 Stock Service  

- FR-11: The Stock Service shall maintain inventory as source of truth.  
- FR-12: The Stock Service shall prevent overselling.  
- FR-13: The Stock Service shall use concurrency control.  
- FR-14: The Stock Service shall reject orders if stock is insufficient.  

---

## 2.4 Kitchen Service  

- FR-15: The Kitchen Service shall process orders asynchronously.  
- FR-16: The Kitchen Service shall update order lifecycle status.  
- FR-17: Kitchen processing shall not block order acknowledgment.  

---

## 2.5 Notification Hub  

- FR-18: The system shall push real-time updates to students.  
- FR-19: The system shall eliminate client-side polling.  

---

## 2.6 Observability  

- FR-20: Each service shall expose a `/health` endpoint.  
- FR-21: Each service shall expose a `/metrics` endpoint.  
- FR-22: Metrics shall include:  
  - Total processed orders  
  - Failure count  
  - Average response latency  

---

## 2.7 CI/CD  

- FR-23: Unit tests shall exist for order validation.  
- FR-24: Unit tests shall exist for stock deduction logic.  
- FR-25: Every push to main shall trigger automated testing.  
- FR-26: The build shall fail if tests fail.  

---

## 2.8 Deployment  

- FR-27: The entire system shall run via `docker compose up`.  
- FR-28: Each service shall run in an isolated container.  

---

# 3️⃣ Non-Functional Requirements  

## 3.1 Performance  

- NFR-1: Order acknowledgment shall be under 2 seconds.  
- NFR-2: Cache shall reduce database load during peak traffic.  

---

## 3.2 Scalability  

- NFR-3: Each service shall scale independently.  
- NFR-4: The system shall avoid single points of failure.  

---

## 3.3 Reliability  

- NFR-5: The system shall tolerate partial service failure.  
- NFR-6: The system shall prevent duplicate order processing.  
- NFR-7: The system shall not lose accepted orders.  

---

## 3.4 Security  

- NFR-8: JWT shall protect all private routes.  
- NFR-9: Passwords shall be stored as hashes only.  
- NFR-10: Rate limiting shall prevent brute-force attacks.  

---

## 3.5 Observability  

- NFR-11: System health shall be externally monitorable.  
- NFR-12: System metrics shall support dashboard visualization.  

---

## 3.6 Maintainability  

- NFR-13: Services shall be independently deployable.  
- NFR-14: The system shall support CI/CD automation.  
- NFR-15: The architecture shall support cloud deployment.  

---

# End of Document