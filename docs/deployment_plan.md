# Deployment & MLOps Phase Tasks

To bring the Hybrid Music Recommendation System to a fully automated production environment, the following infrastructure, deployment, and MLOps tasks must be completed.

---

## 1. MLOps Automation

### A. Nightly ALS Model Retraining Pipeline
* **Task**: Create a batch script (e.g., using Apache Airflow or a simple Kubernetes CronJob) that runs nightly.
* **Flow**:
  1. Extract interaction data from the MongoDB `user_interactions` collection.
  2. Filter out noisy or extremely short play events (e.g., `completion_rate < 0.1`).
  3. Rebuild the sparse User-Item matrix.
  4. Train the Implicit ALS model.
  5. Run offline evaluation against a holdout test set (Precision@K, NDCG@K).
  6. If metrics pass the baseline, serialize and save the model to a versioned artifact store (e.g., S3, MLflow, or local `models/v00X/`).

### B. Feast Feature Synchronization (CDC)
* **Task**: Automate the flow of data from PostgreSQL to the Feast online store.
* **Flow**:
  1. Currently, new song uploads hit PostgreSQL. ML models need this metadata instantly.
  2. Implement a Change Data Capture (CDC) stream (e.g., Debezium) OR a simple background worker (Celery/Kafka) that watches for inserts in PostgreSQL.
  3. Trigger `feast materialize` or push the records directly to the Redis online store so the `HybridRecommendationEngine` can access the freshest catalog items immediately.

---

## 2. Infrastructure & Containerization

### A. Docker Orchestration
* **Task**: Ensure the `docker-compose.yml` (or Kubernetes manifests) covers all required services.
* **Services Required**:
  - `fastapi-backend`: The main API server.
  - `react-frontend`: The Vite UI (served via Nginx).
  - `kafka-broker` & `zookeeper`: For event streaming.
  - `interaction-consumer`: The background Python script reading Kafka and writing to Mongo/Redis.
  - `postgres-db`: Catalog metadata.
  - `mongo-db`: Interactions and preferences.
  - `redis-cache`: Telemetry logs, caching, and Feast online store.
  - `qdrant-vector`: Vector database for audio embeddings.

### B. Secrets Management
* **Task**: Extract all hardcoded configuration strings.
* **Flow**: Ensure database URIs, Kafka bootstraps, and JWT secrets are managed via `.env` files or secure secret managers (e.g., AWS Secrets Manager, HashiCorp Vault) rather than baked into the Docker images.

---

## 3. Scalability & Reliability

### A. API Load Balancing & Scaling
* **Task**: Configure Gunicorn with multiple Uvicorn workers for the FastAPI backend to handle concurrent recommendation requests effectively.

### B. Kafka Consumer Scaling
* **Task**: Ensure the `InteractionConsumer` is designed to be horizontally scaled. By assigning consumer groups properly, multiple consumer instances can process the `recsys_interactions` topic in parallel during high traffic.

---

## 4. Observability & Monitoring

### A. Application Metrics (Prometheus / Grafana)
* **Task**: Add Prometheus middleware to FastAPI.
* **Metrics to Track**:
  - `recommendation_latency_ms`: How long it takes to generate hybrid results.
  - `cache_hit_ratio`: Percentage of requests hitting the Redis recommendation cache vs. computing fresh.
  - `interaction_throughput`: Number of events processed by Kafka per second.

### B. ML Model Monitoring
* **Task**: Track recommendation degradation.
* **Metrics to Track**:
  - Compare the daily click-through rate (CTR) of the recommendations.
  - Track how often the "Cold Start" popularity fallback is triggered versus true personalized hybrid results.

---

## 5. CI/CD Pipeline Setup

* **Task**: Set up GitHub Actions (or GitLab CI).
* **Workflows**:
  - **Lint & Test**: Run `pytest` on the backend and ESLint on the frontend for every pull request.
  - **Build & Push**: Build Docker images and push them to a registry (Docker Hub, ECR) on merge to `master`.
  - **Deploy**: Trigger automated deployments to the staging or production environments.
