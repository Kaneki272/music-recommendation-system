# Frontend Developer Guide

## 1. Repository
This repository contains the backend and ML infrastructure for the Hybrid Music Recommendation System.

## 2. Branch: `frontend-dev`
All frontend development should occur on the `frontend-dev` branch. This branch is strictly isolated from backend infrastructure changes.

## 3. How to Clone
```bash
git clone <repository_url>
cd music-recommendation-system
```

## 4. How to Switch to frontend-dev
```bash
git fetch origin
git checkout frontend-dev
```

## 5. Frontend Setup
The `frontend/` directory is currently a skeleton structure. You may initialize your preferred framework (e.g., Vite, Next.js, Create React App) inside the `frontend/` directory.

## 6. API Base URL Configuration
Ensure that your application uses environment variables for the backend API URL.

**Local Development**: `http://localhost:8000`
**Remote Integration (e.g., ngrok)**: `https://<ngrok-domain>`
**Production**: `https://<production-api-domain>`

Do **not** hardcode URLs in your components. Use the appropriate environment variables for your framework (e.g., `VITE_API_BASE_URL`, `NEXT_PUBLIC_API_BASE_URL`).

## 7. API Endpoints
The frontend must communicate **only** with the FastAPI backend exposed on port 8000 (or the ngrok equivalent).

### 1. Health Check
`GET /health`
Returns system status.

### 2. Recommendations
`GET /api/v1/recommendations/?user_id=<USER_ID>&limit=<LIMIT>`
Returns personalized recommendations for a user.

### 3. Interactions
`POST /api/v1/interactions/`
Submit user interactions (play, skip, like, etc.).

## 8. Recommendation Request Example
```javascript
const response = await fetch(`${API_BASE_URL}/api/v1/recommendations/?user_id=user_000949&limit=10`);
const data = await response.json();
// data.recommendations contains array of { song_id, score, model_name, rank, etc. }
```

## 9. Interaction Request Example
```javascript
const response = await fetch(`${API_BASE_URL}/api/v1/interactions/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: "user_000949",
    event_type: "PLAY",
    track_id: "mbid:08b45156-bdcc-4f48-89cf-fff480eb3313",
    source: "web"
  })
});
```

## 10. Mock API vs Real API Mode

The frontend project is now equipped with a unified API layer that seamlessly switches between a **Mock API** and the **Real FastAPI**. This allows you to work on the UI entirely independently of the backend when needed.

### Configuration
Toggle the mode using the `.env` file in the `frontend/` directory (you can copy `.env.example` to `.env`):

```env
# Set to 'true' to use the Mock API, 'false' to use the Real FastAPI
VITE_USE_MOCK_API=true
VITE_API_BASE_URL=http://localhost:8000
VITE_DEMO_USER_ID=user_000949
```

### How it Works
- **Unified Interface (`src/api/index.js`)**: All UI components import `getRecommendations`, `sendInteraction`, and `getHealth` from here. The components do not care which mode is active.
- **Mock Service (`src/api/mockService.js`)**: Generates realistic dummy responses matching the FastAPI schema exactly. It includes simulated network delays to replicate real-world conditions.
- **Real Service (`src/api/realService.js`)**: Makes actual `fetch()` calls to `VITE_API_BASE_URL`.

### What You Should and Shouldn't Touch
- **DO NOT TOUCH** `src/api/realService.js` or the expected data schema unless the backend contract explicitly changes. This must always perfectly match the FastAPI endpoint signature.
- **YOU MAY MODIFY** `src/api/mockService.js` to change the dummy data (e.g., adding edge cases like empty lists, error simulations) as long as it adheres to the expected backend shape.
- **UI Components**: Feel free to build and modify React components. They should only import from `src/api/index.js`.

## 11. Local Backend URL
Local backend is accessible at: `http://localhost:8000`

## 12. Remote Integration
To interact with a remotely hosted backend, request the active `ngrok` HTTPS URL from the backend engineer. Do not commit this temporary URL to source control.

## 13. What Services Frontend Must NOT Access
The frontend must **NOT** directly connect to:
- MongoDB (27017)
- PostgreSQL (5432)
- Redis (6379)
- Kafka (9092)
- Qdrant (6333)

## 14. Git Workflow
- Work exclusively on the `frontend-dev` branch or its feature branches.
- Do NOT merge `backend-ml` into `frontend-dev`.
- Do NOT modify files outside the `frontend/` and `docs/` directories without backend approval.

## 15. How to Report API Contract Changes
If the UI design requires additional fields (like track metadata, artist info, cover art URLs) that are not present in the current API responses, do NOT try to fetch them from external databases. Instead, report the missing fields to the backend engineer so the FastAPI contracts can be updated.
