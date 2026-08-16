import pandas as pd
import random
import os
from datetime import datetime, timedelta

def generate_fixture():
    print("Generating SYNTHETIC_TEST_DATA fixture...")
    
    users = [f"user_{i}" for i in range(1, 11)]
    songs = [f"song_{i}" for i in range(1, 21)]
    
    rows = []
    base_time = datetime(2026, 1, 1, 12, 0, 0)
    
    for _ in range(100):
        user = random.choice(users)
        song = random.choice(songs)
        # Random time within a 30-day window
        ts = base_time + timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        
        # LastFM style: user_id \t timestamp \t artist_id \t song_id \t track_name
        # We will use epoch timestamps or ISO 8601 strings
        rows.append(f"{user}\t{ts.isoformat()}Z\tartist_1\t{song}\tTrack Name")
        
    # Introduce some deliberate errors for validation
    rows.append(f"user_1\t1960-01-01T00:00:00Z\tartist_1\tsong_1\tTrack Name") # Invalid timestamp
    rows.append(f"\t2026-02-01T00:00:00Z\tartist_1\tsong_1\tTrack Name") # Missing user
    
    # Exact duplicate
    rows.append(rows[0])
    
    os.makedirs("datasets/raw", exist_ok=True)
    with open("datasets/raw/SYNTHETIC_TEST_DATA.tsv", "w") as f:
        f.write("\n".join(rows))
        
    print("Done! Created datasets/raw/SYNTHETIC_TEST_DATA.tsv")

if __name__ == "__main__":
    generate_fixture()
