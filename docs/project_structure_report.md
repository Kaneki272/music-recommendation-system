# Project Structure and Connectivity Report

This document outlines the purpose of every major directory and critical file in the "Hybrid Music Recommendation System", detailing their exact functions and how they connect to one another.

---

## 1. High-Level Folder Overview

| Directory | Primary Function |
| --------- | ---------------- |
| `backend/` | The FastAPI server that acts as the primary API gateway for the frontend, orchestrates the ML models, and manages database connections. |
| `frontend/` | The React (Vite + TypeScript) user interface that users interact with. |
| `ml/` | The Machine Learning domain containing all recommendation algorithms, scoring logic, and data contracts. |
| `streaming/` | Event-driven architecture components (Kafka producers and consumers) for handling asynchronous user interactions. |
| `feature_store/` | Integration with Feast and Qdrant to serve features to the ML models. |
| `docs/` | Project documentation and audit reports. |
| `docker/` | Dockerfiles and container configurations. |

---

## 2. Directory & File Breakdown

### A. The Backend (`/backend`)
Handles the REST API, dependency injection, and data access.

* **`backend/main.py`**
  * **Function**: The application entry point. Initializes database connections (PostgreSQL, MongoDB, Redis) and registers API routers.
  * **Connected to**: `backend/dependencies/database.py`, API routers, and Docker environment variables.

* **`backend/api/v1/`** (API Routes)
  * **`recommendations/router.py`**: Exposes `GET /api/v1/recommendations/`. Connects to `HybridRecommendationEngine` and hydrates track metadata using `backend/api/v1/songs/router.py`.
  * **`interactions/router.py`**: Exposes `POST /api/v1/interactions/`. Receives interactions (Play, Like) and passes them to `streaming/producers/interaction_producer.py`.
  * **`songs/router.py`**: Handles audio catalog retrieval, physical audio file streaming, file uploads, and targeted acoustic similarity (Song Radio). Connects to Qdrant for vector upserts.

* **`backend/dependencies/`** (Dependency Injection)
  * **`database.py`**: Creates singleton connection pools for Mongo, Postgres, and Redis.
  * **`models.py`**: Initializes the heavy ML models (ALS, Content-Based, Popularity) and the `HybridRecommendationEngine` into memory at startup.

* **`backend/database/` & `backend/repositories/`** (Data Access)
  * **`qdrant/client.py`**: Implements Qdrant queries for the 215-D audio vectors. Used heavily by the Content-Based model and the `songs` router.
  * **`repositories/interaction.py`**: Abstraction over MongoDB to count user interactions. Connected to the `recommendations` router to determine if a user is `NEW_USER` or `KNOWN_USER`.

### B. The Machine Learning Core (`/ml`)
Houses the recommendation logic. It is completely decoupled from HTTP frameworks.

* **`ml/contracts/`** (Data Schemas)
  * **`identifiers.py`**: Defines strictly typed canonical IDs (e.g., 215-D vector rule, `SongId`, `UserId`). Prevents type confusion across the system.
  * **`recommendations.py`**: Defines `RecommendationRequest` and `RecommendationResponse`.

* **`ml/hybrid/engine.py`**
  * **Function**: The brain of the recommendation system. It evaluates the user's interaction count, assigns dynamic weights to models, orchestrates the retrieval from ALS, Content, and Popularity models, deduplicates candidates, and passes them to the scorer.
  * **Connected to**: `backend/api/v1/recommendations/router.py` (Called by), `ml/collaborative/model.py` (Calls), `ml/content_based/model.py` (Calls).

* **`ml/collaborative/`**, **`ml/content_based/`**, **`ml/popularity/`**
  * **Function**: The individual recommendation models. The Collaborative model uses Implicit ALS. The Content model relies on Qdrant audio vectors and Feast metadata. The Popularity model relies on baseline trends.

### C. The Streaming Pipeline (`/streaming`)
Decouples interaction writes from the main API thread using Kafka.

* **`streaming/schemas/events.py`**: Defines the `MusicEvent` schema to ensure all Kafka events share the same structure.
* **`streaming/producers/interaction_producer.py`**: 
  * **Function**: Sends `MusicEvent` payloads to the Kafka broker.
  * **Connected to**: `backend/api/v1/interactions/router.py` (Called by).
* **`streaming/consumers/interaction_consumer.py`**:
  * **Function**: A standalone Python script running infinitely in the background. It reads from Kafka, assigns ML weights to the interactions, saves the permanent record to MongoDB, and pushes the recent track to Redis.
  * **Connected to**: Kafka (Reads from), MongoDB (Writes to), Redis (Writes to).

### D. The Feature Store (`/feature_store`)
* **`feature_store/feast_provider.py`**
  * **Function**: Implements `FeatureProviderInterface`. It acts as a bridge so ML models don't need to know *where* data is stored. It fetches structured metadata from Feast (Redis) and dense audio vectors from Qdrant, merging them into a unified `ContentRepresentation`.
  * **Connected to**: `backend/dependencies/models.py` (Initialized in), `ml/content_based/model.py` (Used by).

### E. The Frontend (`/frontend`)
React application built with Vite and TailwindCSS.

* **`frontend/src/App.tsx` & `main.tsx`**: Entry points, router definitions, and global state initialization.
* **`frontend/src/pages/Home.tsx`**: 
  * **Function**: The primary dashboard for the user. Handles the loading state, the "warming up" cold-start state, and rendering the grid of recommendations.
  * **Connected to**: `frontend/src/api/recommendations.ts` (Fetches data).
* **`frontend/src/components/recommendation/RecommendationCard.tsx`**:
  * **Function**: Renders individual song cards with glassmorphism UI. Handles Play, Like, and Skip actions via hover overlays.
  * **Connected to**: `frontend/src/api/interactions.ts` (Sends clicks to backend).
* **`frontend/src/api/`**:
  * **Function**: Axios HTTP clients. `recommendations.ts` explicitly maps the complex nested backend `RecommendationResponse` into a flat array structure expected by the React components.

---

## 3. Core System Connections (How Data Flows)

### Flow 1: Recommendation Retrieval
1. **`frontend/src/pages/Home.tsx`** mounts and calls `getRecommendations()`.
2. **`frontend/src/api/recommendations.ts`** fires HTTP GET to `/api/v1/recommendations/`.
3. **`backend/api/v1/recommendations/router.py`** intercepts the request.
4. Router invokes **`backend/repositories/interaction.py`** to check MongoDB for the user's interaction count.
5. Router passes the count to **`ml/hybrid/engine.py`**.
6. The Engine queries **`ml/collaborative/model.py`**, **`ml/content_based/model.py`**, and **`ml/popularity/model.py`**.
7. The Content model calls **`feature_store/feast_provider.py`**, which queries **`backend/database/qdrant/client.py`** and Feast.
8. The Engine scores, ranks, and returns the top `song_id`s.
9. **`backend/api/v1/recommendations/router.py`** hydrates these IDs into actual titles using **`backend/api/v1/songs/router.py`** and returns the JSON.
10. The UI renders the data in **`RecommendationCard.tsx`**.

### Flow 2: User Interaction (Like / Play)
1. User clicks the "Like" button on **`RecommendationCard.tsx`**.
2. **`frontend/src/api/interactions.ts`** fires HTTP POST to `/api/v1/interactions/`.
3. **`backend/api/v1/interactions/router.py`** receives the request and creates a `MusicEvent`.
4. It passes the event to **`streaming/producers/interaction_producer.py`**, which pushes it to Kafka.
5. The API immediately responds `200 OK` to the frontend (fast response).
6. In the background, **`streaming/consumers/interaction_consumer.py`** pulls the event from Kafka.
7. The Consumer writes the interaction to **MongoDB** (`user_interactions` collection) and updates the user's recent tracks list in **Redis**.
8. Future queries to the recommendation engine will now account for this new data point.
