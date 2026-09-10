"""
Kafka producer for user interaction events.
Serializes canonical MusicEvent schemas to JSON and publishes to Kafka.
"""
import json
from kafka import KafkaProducer
from streaming.schemas.events import MusicEvent
from backend.config.settings import settings

class InteractionProducer:
    """Publishes canonical MusicEvents to Kafka."""

    def __init__(self):
        brokers = settings.KAFKA_BOOTSTRAP_SERVERS
        print(f"InteractionProducer connecting to brokers: {brokers}")
        self.producer = KafkaProducer(
            bootstrap_servers=brokers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retries=3,
        )

    def publish_event(self, event: MusicEvent) -> None:
        """
        Publish a single MusicEvent.
        Uses user_id as the partition key for ordering guarantees.
        """
        topic = settings.KAFKA_INTERACTION_TOPIC
        
        # Convert pydantic model to json dictionary
        event_dict = event.model_dump(mode="json")
        
        # Add a schema version marker for safety
        event_dict["schema_version"] = "1.0"
        
        self.producer.send(
            topic=topic,
            key=event.user_id,
            value=event_dict,
        )
        self.producer.flush()

    def close(self):
        self.producer.close()
