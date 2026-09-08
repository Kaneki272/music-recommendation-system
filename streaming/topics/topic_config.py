"""
Kafka topic definitions for the Music Recommendation System.
"""

TOPICS = {
    "user.interactions": {
        "partitions": 3,
        "replication_factor": 1,
        "description": "All user interaction events (play, like, skip, etc.)",
    },
    "recommendations.served": {
        "partitions": 2,
        "replication_factor": 1,
        "description": "Recommendation batches served to users",
    },
    "recommendations.feedback": {
        "partitions": 2,
        "replication_factor": 1,
        "description": "User clicks/ignores on served recommendations",
    },
    "catalog.updates": {
        "partitions": 1,
        "replication_factor": 1,
        "description": "New songs/artists added to catalog",
    },
}
