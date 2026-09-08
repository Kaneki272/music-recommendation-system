import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from qdrant_client import AsyncQdrantClient
from backend.config.settings import settings

async def main():
    print("=== Database Validation ===")
    
    # 1. MongoDB
    mongo = AsyncIOMotorClient(settings.MONGO_URI)
    db = mongo[settings.MONGO_DATABASE]
    user_interactions = await db["user_interactions"].count_documents({})
    print(f"MongoDB 'user_interactions' count: {user_interactions}")
    
    # 2. Redis
    import redis.asyncio as redis
    redis_client = redis.from_url(settings.REDIS_URI)
    await redis_client.ping()
    print("Redis: OK")
    
    # 3. Postgres
    # Skipping direct connection, healthcheck will do it.
    
    # 4. Qdrant
    qdrant = AsyncQdrantClient(url=settings.QDRANT_URI)
    collection_name = "audio_features"
    try:
        collections = await qdrant.get_collections()
        print(f"Qdrant collections: {[c.name for c in collections.collections]}")
        for c in collections.collections:
            col_info = await qdrant.get_collection(collection_name=c.name)
            print(f" - {c.name}: dim={col_info.config.params.vectors.size}, count={col_info.points_count}")
    except Exception as e:
        print(f"Qdrant error: {e}")
        
    print("\n=== Recommendation Validation ===")
    async with httpx.AsyncClient() as http_client:
        user_id = "user_000949"
        res = await http_client.get(f"http://localhost:8000/api/v1/recommendations/?user_id={user_id}&limit=5")
        if res.status_code == 200:
            data = res.json()
            print(f"[{user_id}] state: {data['metadata']['user_state']}")
            print(f"[{user_id}] metadata: {data['metadata']}")
            print(f"[{user_id}] final weights: {data['metadata'].get('active_weights', 'N/A')}")
            print(f"[{user_id}] recommendations:")
            for r in data["recommendations"]:
                print(f" - {r}")
        else:
            print(f"API Error: {res.text}")
            
        print("\n=== Cold Start Validation ===")
        new_user = "audit_user_999"
        res2 = await http_client.get(f"http://localhost:8000/api/v1/recommendations/?user_id={new_user}&limit=5")
        if res2.status_code == 200:
            data2 = res2.json()
            print(f"[{new_user}] state: {data2['metadata']['user_state']}")
        
        print("\nSending interaction for new user...")
        await http_client.post("http://localhost:8000/api/v1/interactions/", json={
            "user_id": new_user,
            "song_id": "test_song_xyz",
            "interaction_type": "play",
            "weight": 1.0
        })
        
        await asyncio.sleep(2)
        res3 = await http_client.get(f"http://localhost:8000/api/v1/recommendations/?user_id={new_user}&limit=5")
        if res3.status_code == 200:
            data3 = res3.json()
            print(f"[{new_user}] state after interaction: {data3['metadata']['user_state']}")

if __name__ == "__main__":
    asyncio.run(main())
