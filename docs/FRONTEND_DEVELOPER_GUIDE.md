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

## 10. Mock-Data Development Mode
If the backend is offline, you should build mock data handlers (e.g., using MSW or conditional hardcoded JSON) returning dummy recommendation cards to unblock UI development.

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
