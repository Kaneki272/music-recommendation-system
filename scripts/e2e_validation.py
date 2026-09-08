import asyncio
import httpx
import time
import subprocess
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config.settings import settings

async def main():
    print("=== Step A: Baseline ===")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DATABASE]
    
    user_id = "user_000949"
    new_user_id = "user_unknown_123"
    
    count_before = await db["user_interactions"].count_documents({"user_id": user_id})
    print(f"[{user_id}] Initial count: {count_before}")
    
    new_count_before = await db["user_interactions"].count_documents({"user_id": new_user_id})
    print(f"[{new_user_id}] Initial count: {new_count_before}")

    async with httpx.AsyncClient() as http_client:
        # Check current recommendations
        res = await http_client.get(f"http://localhost:8000/api/v1/recommendations/?user_id={user_id}&limit=5")
        if res.status_code == 200:
            print(f"[{user_id}] Initial state: {res.json()['metadata']['user_state']}")
        else:
            print(f"[{user_id}] Initial API error: {res.text}")
            
        res2 = await http_client.get(f"http://localhost:8000/api/v1/recommendations/?user_id={new_user_id}&limit=5")
        if res2.status_code == 200:
            print(f"[{new_user_id}] Initial state: {res2.json()['metadata']['user_state']}")
            
        print("\n=== Step B: Publish Event ===")
        print(f"Sending POST to /api/v1/interactions/ for both users...")
        
        post1 = await http_client.post("http://localhost:8000/api/v1/interactions/", json={
            "user_id": user_id,
            "song_id": "test_song_1",
            "interaction_type": "play",
            "weight": 1.0
        })
        print(f"[{user_id}] Publish Response: {post1.status_code} {post1.json()}")
        
        post2 = await http_client.post("http://localhost:8000/api/v1/interactions/", json={
            "user_id": new_user_id,
            "song_id": "test_song_2",
            "interaction_type": "like",
            "weight": 4.0
        })
        print(f"[{new_user_id}] Publish Response: {post2.status_code} {post2.json()}")
        
    print("\n=== Waiting for Consumer ===")
    print("Sleeping for 3 seconds to let Kafka Consumer process...")
    await asyncio.sleep(3)
    
    print("\n=== Step D & E: Persistence & Updated State ===")
    count_after = await db["user_interactions"].count_documents({"user_id": user_id})
    print(f"[{user_id}] Final count: {count_after}")
    
    new_count_after = await db["user_interactions"].count_documents({"user_id": new_user_id})
    print(f"[{new_user_id}] Final count: {new_count_after}")
    
    async with httpx.AsyncClient() as http_client:
        res = await http_client.get(f"http://localhost:8000/api/v1/recommendations/?user_id={user_id}&limit=5")
        if res.status_code == 200:
            print(f"[{user_id}] Final state: {res.json()['metadata']['user_state']}")
            print(f"[{user_id}] Final weights: {res.json()['metadata']['active_weights']}")
            
        res2 = await http_client.get(f"http://localhost:8000/api/v1/recommendations/?user_id={new_user_id}&limit=5")
        if res2.status_code == 200:
            print(f"[{new_user_id}] Final state: {res2.json()['metadata']['user_state']}")
            print(f"[{new_user_id}] Final weights: {res2.json()['metadata']['active_weights']}")

if __name__ == "__main__":
    asyncio.run(main())
