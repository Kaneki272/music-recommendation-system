import argparse
import os
import json
from ml.datasets.adapters import LastFmAdapter
from ml.datasets.validator import DatasetValidator
from ml.datasets.stats import DatasetStatistics

def validate_dataset(filepath: str, source_name: str):
    print(f"Validating dataset: {filepath}")
    
    # 1. Choose adapter
    adapter = LastFmAdapter(filepath, chunksize=100_000)
    validator = DatasetValidator(min_user_interactions=5, min_song_interactions=5)
    stats = DatasetStatistics()
    
    total_dropped = {
        "missing_ids": 0,
        "invalid_timestamp": 0,
        "invalid_type": 0,
        "invalid_weight": 0,
        "exact_duplicates": 0
    }
    
    # 2. Chunked validation
    print("Running chunked validation...")
    for i, chunk in enumerate(adapter.iter_chunks()):
        valid_chunk, chunk_dropped = validator.validate_chunk(chunk)
        
        for k in total_dropped:
            total_dropped[k] += chunk_dropped[k]
            
        stats.update(valid_chunk)
        print(f"  Validated chunk {i+1} (Rows retained: {len(valid_chunk)})")

    print("\n================ VALIDATION REPORT ================")
    print("Dropped Rows by Reason:")
    for k, v in total_dropped.items():
        print(f"  - {k}: {v}")
        
    final_stats = stats.finalize()
    print("\nDataset Statistics (Valid Rows Only):")
    print(json.dumps(final_stats, indent=2))
    
    users_below = sum(1 for v in stats.user_counts.values() if v < validator.min_user_interactions)
    songs_below = sum(1 for v in stats.song_counts.values() if v < validator.min_song_interactions)
    print("\nOrphan Analysis:")
    print(f"  Users below {validator.min_user_interactions} interactions: {users_below}")
    print(f"  Songs below {validator.min_song_interactions} interactions: {songs_below}")
    print("===================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a raw dataset without saving output.")
    parser.add_argument("filepath", type=str, help="Path to raw dataset.")
    parser.add_argument("--source", type=str, default="lastfm", help="Dataset source (lastfm, etc.)")
    args = parser.parse_args()
    
    validate_dataset(args.filepath, args.source)
