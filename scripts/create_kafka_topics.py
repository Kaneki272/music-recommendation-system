import os
import sys

# Add project root to python path so we can import from streaming
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kafka.admin import KafkaAdminClient, NewTopic
from streaming.topics.topic_config import TOPICS

def create_topics():
    brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    print(f"Connecting to Kafka brokers: {brokers}")
    
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=brokers.split(","),
            client_id="recsys_admin"
        )
        
        # Get existing topics to avoid errors
        existing_topics = admin_client.list_topics()
        print(f"Existing topics: {existing_topics}")
        
        topic_list = []
        for name, config in TOPICS.items():
            if name not in existing_topics:
                topic = NewTopic(
                    name=name,
                    num_partitions=config["partitions"],
                    replication_factor=config["replication_factor"]
                )
                topic_list.append(topic)
                print(f"Prepared to create topic: {name}")
            else:
                print(f"Topic '{name}' already exists.")
                
        if topic_list:
            admin_client.create_topics(new_topics=topic_list, validate_only=False)
            print("Successfully created new topics.")
        else:
            print("No new topics to create.")
            
        admin_client.close()
        
    except Exception as e:
        print(f"Failed to create topics: {e}")

if __name__ == "__main__":
    create_topics()
