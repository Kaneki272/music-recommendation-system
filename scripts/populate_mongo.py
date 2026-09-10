import asyncio
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config.settings import settings

async def populate_mongo():
    print("Loading train.parquet...")
    df = pd.read_parquet("datasets/processed/lastfm/train.parquet")
    
    print(f"Total interactions in parquet: {len(df)}")
    
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DATABASE]
    collection = db["user_interactions"]
    
    # Check if already populated
    count = await collection.count_documents({})
    if count > 0:
        print(f"MongoDB already has {count} documents. Skipping population.")
        return
        
    print("Converting to dict...")
    records = []
    # Only populate for our test users to make it fast
    target_users = {"user_000949", "user_000001", "user_000791"}
    
    for row in df.itertuples():
        if row.user_id in target_users:
            records.append({
                "user_id": row.user_id,
                "item_id": row.song_id,
                "item_type": "song",
                "interaction_type": row.interaction_type,
                "timestamp": row.timestamp
            })
        
    print(f"Inserting {len(records)} records into MongoDB in chunks...")
    chunk_size = 50000
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        await collection.insert_many(chunk)
        print(f"Inserted {i + len(chunk)} / {len(records)}")
        
    print("Creating index on user_id...")
    await collection.create_index("user_id")
    print("Done!")

if __name__ == "__main__":
    asyncio.run(populate_mongo())
