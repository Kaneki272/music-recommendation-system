"""
Synthetic event generator for pipeline testing.
Produces realistic interaction events using the canonical MusicEvent.
"""
import uuid
import random
import time
import os
import sys

# Add project root to python path for standalone execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streaming.schemas.events import MusicEvent
from streaming.producers.interaction_producer import InteractionProducer

# Use mock identifiers for testing
SAMPLE_SONGS = [f"song_{str(i).zfill(3)}" for i in range(1, 21)]
SAMPLE_USERS = [f"user_{str(i).zfill(3)}" for i in range(1, 6)]

def generate_events(events_per_second: float = 1.0):
    print(f"Starting synthetic event generator at {events_per_second} events/sec...")
    producer = InteractionProducer()
    
    try:
        while True:
            user_id = random.choice(SAMPLE_USERS)
            track_id = random.choice(SAMPLE_SONGS)
            
            # 70% plays, 15% likes, 15% skips
            roll = random.random()
            
            if roll < 0.70:
                event_type = "PLAY"
                duration = random.randint(30000, 240000)
                completion = random.uniform(0.91, 1.0) if random.random() < 0.3 else random.uniform(0.1, 0.89)
            elif roll < 0.85:
                event_type = "LIKE"
                duration = None
                completion = None
            else:
                event_type = "SKIP"
                duration = random.randint(3000, 30000)
                completion = None
                
            event = MusicEvent(
                event_id=str(uuid.uuid4()),
                user_id=user_id,
                track_id=track_id,
                event_type=event_type,
                source="synthetic",
                duration_played_ms=duration,
                completion_rate=completion,
            )
            
            producer.publish_event(event)
            print(f"Produced: {event_type} for {user_id} on {track_id} (ID: {event.event_id})")
            time.sleep(1.0 / events_per_second)
            
    except KeyboardInterrupt:
        print("Stopping synthetic event generator.")
        producer.close()

if __name__ == "__main__":
    generate_events(events_per_second=2.0)
