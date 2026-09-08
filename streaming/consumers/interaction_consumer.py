"""
Kafka consumer for user interaction events.
Reads from Kafka, validates against canonical MusicEvent,
normalizes, and persists to MongoDB and Redis.
"""
import json
import os
import sys
import asyncio
from datetime import datetime
import pymongo
from pymongo.errors import DuplicateKeyError

# Add project root to python path for standalone execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from kafka import KafkaConsumer
from streaming.schemas.events import MusicEvent
from ml.contracts.interactions import InteractionRecord, InteractionType, InteractionWeightConfig
from backend.config.settings import settings
import motor.motor_asyncio
import redis.asyncio as aioredis

class InteractionConsumer:
    """Consumes MusicEvents, validates, and writes to MongoDB and Redis."""

    def __init__(self, group_id: str = "recsys-interaction-consumer"):
        brokers = settings.KAFKA_BOOTSTRAP_SERVERS
        print(f"InteractionConsumer connecting to brokers: {brokers}")
        
        self.consumer = KafkaConsumer(
            settings.KAFKA_INTERACTION_TOPIC,
            bootstrap_servers=brokers.split(","),
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False, # We commit manually after persistence
        )
        self.weight_config = InteractionWeightConfig()
        
        # Initialize async clients for the consumer process
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.mongo_client[settings.MONGO_DATABASE]
        self.interactions_col = self.db["user_interactions"]
        self.redis_client = aioredis.from_url(settings.REDIS_URI, decode_responses=True)

    async def _setup_indexes(self):
        """Ensure unique index on event_id for idempotency."""
        await self.interactions_col.create_index("event_id", unique=True, sparse=True)
        await self.interactions_col.create_index("user_id")
        await self.interactions_col.create_index("track_id")

    async def _process_event(self, event: MusicEvent) -> bool:
        """
        Process a validated event.
        Converts to InteractionRecord and writes to MongoDB and Redis.
        Returns True if successful (or duplicate), False if failed.
        """
        interaction_type = None
        weight = 0.0
        
        # Normalize event_type to InteractionType
        if event.event_type == "PLAY":
            interaction_type = InteractionType.PLAY
            weight = self.weight_config.get_weight(InteractionType.PLAY)
            if event.completion_rate and event.completion_rate > 0.9:
                 interaction_type = InteractionType.COMPLETE
                 weight = self.weight_config.get_weight(InteractionType.COMPLETE)
        elif event.event_type == "LIKE":
            interaction_type = InteractionType.LIKE
            weight = self.weight_config.get_weight(InteractionType.LIKE)
        elif event.event_type == "SKIP":
            if event.duration_played_ms and event.duration_played_ms < 30000:
                interaction_type = InteractionType.SKIP_EARLY
                weight = self.weight_config.get_weight(InteractionType.SKIP_EARLY)
            else:
                interaction_type = InteractionType.SKIP
                weight = self.weight_config.get_weight(InteractionType.SKIP)

        if not interaction_type:
             print(f"Could not map event type {event.event_type} to interaction type.")
             return False
             
        record = InteractionRecord(
            user_id=event.user_id,
            song_id=event.track_id,
            interaction_type=interaction_type,
            timestamp=event.timestamp,
            weight=weight,
            source=event.source,
            session_id=event.session_id,
        )
        
        doc = record.model_dump()
        doc["event_id"] = event.event_id  # explicitly include event_id for idempotency
        
        # 1. MongoDB Persistence
        try:
            await self.interactions_col.insert_one(doc)
            print(f"→ [MONGO SAVED] {record.interaction_type.value.upper():10} | User: {record.user_id:12} | Song: {record.song_id:12} | Weight: {record.weight}")
        except DuplicateKeyError:
            print(f"→ [DUPLICATE] Event {event.event_id} already exists. Ignoring.")
        except Exception as e:
            print(f"→ [MONGO ERROR] Failed to persist event {event.event_id}: {e}")
            return False
            
        # 2. Redis State Update (Recent Tracks)
        try:
            redis_key = f"user:{event.user_id}:recent_tracks"
            await self.redis_client.lpush(redis_key, event.track_id)
            await self.redis_client.ltrim(redis_key, 0, 49) # Keep only latest 50
        except Exception as e:
            print(f"→ [REDIS ERROR] Failed to update state for user {event.user_id}: {e}")
            # We don't fail the whole event if Redis fails, but in strict systems we might.
            # We will just log it here.
            
        return True

    async def _consume_loop(self):
        """Async wrap around the synchronous kafka polling."""
        print("Consumer started. Waiting for messages...")
        await self._setup_indexes()
        
        try:
            # We use a non-blocking poll in an async loop to allow graceful shutdown and async processing
            while True:
                # poll(timeout_ms=100) returns a dict of {TopicPartition: [ConsumerRecord]}
                msg_pack = await asyncio.to_thread(self.consumer.poll, 100)
                for tp, messages in msg_pack.items():
                    for message in messages:
                        try:
                            data = message.value
                            # If older schemas sent 'event_type' inside payload, we use it or default
                            # In MusicEvent we added it properly.
                            event = MusicEvent(**data)
                            
                            success = await self._process_event(event)
                            
                            # Acknowledge after successful processing
                            if success:
                                # We could commit specific offsets, but for simplicity we commit all here
                                # In production, commit the exact offset of the processed message
                                self.consumer.commit()
                            
                        except Exception as e:
                            print(f"Error processing message: {e}")
                
                await asyncio.sleep(0.01)
                
        except asyncio.CancelledError:
            pass
        finally:
            self.consumer.close()
            self.mongo_client.close()
            await self.redis_client.close()

    def run(self):
        """Entry point for the consumer process."""
        try:
            asyncio.run(self._consume_loop())
        except KeyboardInterrupt:
            print("Consumer stopped manually.")

if __name__ == "__main__":
    consumer = InteractionConsumer()
    consumer.run()
