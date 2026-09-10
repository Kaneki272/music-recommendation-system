# Fix Recommendation & Interaction Pipeline End-to-End

## Root Cause Analysis

I did a deep audit. Here is exactly what's broken and why:

### Problem 1: The backend is returning HARDCODED dummy data
The `/api/v1/recommendations/user/{user_id}` endpoint returns **identical results for every user** — same songs, same order, same `"Trending Globally"` reason, same `picsum.photos` cover images. I confirmed this by calling the API with two completely different user IDs and getting byte-for-byte identical responses.

The string `"Trending Globally"` and `picsum.photos` **don't exist anywhere in the Python source code**. This means the running backend process (PID 6884) loaded code from a **previous session** that hardcoded these responses. The current source code on disk has the real ML hybrid engine, but the running process never picked it up.

### Problem 2: The interaction API endpoint doesn't match
- The **frontend** posts interactions to `/api/v1/analytics/interaction` (the OpenAPI schema endpoint)  
- But the **actual router** in [router.py](file:///c:/Users/ACER/Desktop/coding%20stuff/Recommen3/music-recommendation-system/backend/api/v1/interactions/router.py) defines the endpoint at `/api/v1/interactions/` (which would need Kafka running)
- The `analytics` directory is **empty** (just a `.gitkeep`)
- So **interactions are being silently swallowed** — the frontend thinks it succeeded but the data goes nowhere

### Problem 3: The recommendation engine requires databases that aren't running
The real [HybridRecommendationEngine](file:///c:/Users/ACER/Desktop/coding%20stuff/Recommen3/music-recommendation-system/ml/hybrid/engine.py) needs:
- PostgreSQL (for song metadata)
- MongoDB (for interaction history)  
- Qdrant (for vector similarity)
- Kafka (for interaction event streaming)
- Pre-trained ML model artifacts in `models/`

None of these are running natively. Docker failed to build. So even if we restart the backend, the hybrid engine will crash with `503: Recommendation Engine not initialized`.

> [!IMPORTANT]
> **The solution**: We need to bypass the broken infrastructure dependencies and build a **self-contained recommendation pipeline** that works with just the local filesystem (216 audio files) and an in-memory interaction store. This is the only way to make the system actually work on your machine right now.

## Proposed Changes

### Backend — New Lightweight Recommendation Router

#### [MODIFY] [router.py](file:///c:/Users/ACER/Desktop/coding%20stuff/Recommen3/music-recommendation-system/backend/api/v1/songs/router.py)
Add three new endpoints directly in the songs router (which already works and reads from the filesystem):

1. **`GET /songs/trending`** — Returns all 216 songs sorted by a computed popularity score
2. **`GET /recommendations/user/{user_id}`** — Returns **personalized** recommendations:
   - Reads the user's interaction history from an in-memory store
   - Filters OUT songs the user has SKIPPED
   - Boosts songs similar to ones the user has LIKED/PLAYED
   - Falls back to trending for new users (cold start)
3. **`POST /analytics/interaction`** — Stores interactions in-memory AND to a local JSON file so they persist across restarts:
   - Accepts `{user_id, song_id, interaction_type, timestamp}`
   - Stores in a dict keyed by user_id
   - On next recommendation request, uses this data to personalize results

#### [MODIFY] [main.py](file:///c:/Users/ACER/Desktop/coding%20stuff/Recommen3/music-recommendation-system/backend/main.py)
- Remove the dependency on Kafka, MongoDB, and broken recommendation router
- Keep only the songs router (which has the new endpoints)
- Make startup graceful (don't crash if databases aren't available)

---

### Frontend — Wire Up Real Interaction Feedback Loop

#### [MODIFY] [Home.tsx](file:///c:/Users/ACER/Desktop/coding%20stuff/Recommen3/music-recommendation-system/frontend/src/pages/Home.tsx)
- After a LIKE/SKIP interaction, **invalidate the recommendations query** so React Query refetches fresh personalized results
- This creates the "skip a song → reload → see different songs" behavior the user expects

#### [MODIFY] [RecommendationCard.tsx](file:///c:/Users/ACER/Desktop/coding%20stuff/Recommen3/music-recommendation-system/frontend/src/components/recommendation/RecommendationCard.tsx)
- After posting an interaction, call `queryClient.invalidateQueries(['recommendations'])` to trigger a refetch
- Add visual toast/notification feedback: "Liked! Recommendations updated"

#### [MODIFY] [GlobalPlayer.tsx](file:///c:/Users/ACER/Desktop/coding%20stuff/Recommen3/music-recommendation-system/frontend/src/components/player/GlobalPlayer.tsx)
- On PLAY and COMPLETE interactions, also invalidate recommendations

## How Personalization Will Work

```
User skips "Thunder" and "Lalala"
  → Frontend POSTs to /analytics/interaction with type=SKIP
  → Backend stores: user u345678 skipped Thunder, Lalala
  → Frontend invalidates recommendations query  
  → Frontend calls GET /recommendations/user/u345678
  → Backend reads user's interaction history
  → Backend EXCLUDES Thunder and Lalala from results
  → Backend BOOSTS songs similar to ones user LIKED
  → User sees completely different songs
```

## Verification Plan

### Manual Verification
1. Restart the backend after changes
2. Open frontend, login as user A → see recommendations
3. Skip 3 songs → page auto-refreshes → those 3 songs disappear
4. Like 2 songs → recommendations shift toward similar content
5. Login as user B → see completely different (default trending) recommendations
6. Reload page → skipped songs stay gone (persisted to file)
