"""
Sync Pipeline: Postgres/Mongo -> Feast (Parquet -> Redis)
===========================================================
Extracts metadata and behavioral data, writes to Parquet (Offline store),
and triggers Feast materialize to push to Redis (Online store).
"""
import pandas as pd
import json
import os
from datetime import datetime

class FeastMaterializationJob:
    """
    Generates the offline Parquet files used by Feast and 
    invokes the `feast materialize` command.
    """
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.data_dir = os.path.join(repo_path, "data")
        os.makedirs(self.data_dir, exist_ok=True)

    def generate_song_metadata_parquet(self, data: list):
        """
        Converts Postgres song records to the Feast schema and writes Parquet.
        """
        if not data:
            return
            
        df = pd.DataFrame(data)
        
        # Ensure event_timestamp is present
        if "event_timestamp" not in df.columns:
            df["event_timestamp"] = pd.to_datetime(datetime.utcnow())
            
        # Serialize lists/dicts to JSON strings for Feast compatibility
        if "genres" in df.columns:
            df["genres"] = df["genres"].apply(lambda x: json.dumps(x) if isinstance(x, list) else json.dumps([]))
            
        parquet_path = os.path.join(self.data_dir, "song_metadata.parquet")
        # In a real pipeline, we would append or partition. For simplicity:
        df.to_parquet(parquet_path)
        
    def generate_user_behavior_parquet(self, data: list):
        """
        Converts MongoDB aggregation results to the Feast schema and writes Parquet.
        """
        if not data:
            return
            
        df = pd.DataFrame(data)
        
        if "event_timestamp" not in df.columns:
            df["event_timestamp"] = pd.to_datetime(datetime.utcnow())
            
        for col in ["recently_played_ids", "favorite_genres", "acoustic_preferences"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else "[]")
                
        parquet_path = os.path.join(self.data_dir, "user_behavior.parquet")
        df.to_parquet(parquet_path)

    def trigger_materialization(self):
        """
        Calls feast materialize via subprocess to sync offline (Parquet) 
        to online (Redis).
        """
        import subprocess
        
        # feast materialize-incremental $(date -u +"%Y-%m-%dT%H:%M:%S")
        end_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        
        cmd = ["feast", "materialize-incremental", end_time]
        try:
            # We run this in the repo_path directory
            result = subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True, text=True)
            print(f"Materialization successful: {result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"Materialization failed: {e.stderr}")
            raise e
