"""
Feast Entity Definitions
========================
Maps to canonical identifiers from ml/contracts/identifiers.py
"""
from feast import Entity

# Canonical ML keys
song = Entity(
    name="song_id",
    join_keys=["song_id"],
    description="Canonical internal song UUID",
)

user = Entity(
    name="user_id",
    join_keys=["user_id"],
    description="Canonical internal user UUID",
)
