import argparse
import os
import json
import pandas as pd
from datetime import datetime
import pyarrow as pa
import pyarrow.parquet as pq

from ml.datasets.adapters import LastFmAdapter
from ml.datasets.validator import DatasetValidator
from ml.datasets.stats import DatasetStatistics
from ml.datasets.splitter import ChronologicalSplitter

def prepare_dataset(filepath: str, source_name: str, output_dir: str):
    print(f"Preparing dataset: {filepath}")
    
    # 1. Choose adapter (Hardcoded for LastFM style for this demo)
    adapter = LastFmAdapter(filepath, chunksize=500_000)
    validator = DatasetValidator(min_user_interactions=5, min_song_interactions=5, drop_orphans=False)
    stats = DatasetStatistics()
    
    intermediate_path = os.path.join("datasets", "intermediate", "canonical.parquet")
    
    # Prepare parquet writer
    schema = pa.schema([
        ('user_id', pa.string()),
        ('song_id', pa.string()),
        ('interaction_type', pa.string()),
        ('timestamp', pa.timestamp('ns')),
        ('weight', pa.float32()),
        ('source', pa.string()),
        ('session_id', pa.string()),
        ('identity_resolution_method', pa.string()),
        ('identity_confidence', pa.string()),
        ('source_user_id', pa.string()),
        ('source_track_id', pa.string()),
        ('source_artist_id', pa.string())
    ])
    
    total_dropped = {
        "unresolved_identity": 0,
        "missing_ids": 0,
        "invalid_timestamp": 0,
        "invalid_type": 0,
        "invalid_weight": 0,
        "exact_duplicates": 0
    }
    
    total_raw_rows = 0
    total_valid_rows = 0
    
    # 2. Chunked reading, validation, and writing to intermediate Parquet
    print("Step 1: Chunked Validation and Normalization...")
    with pq.ParquetWriter(intermediate_path, schema) as writer:
        for i, chunk in enumerate(adapter.iter_chunks()):
            raw_chunk_len = len(chunk)
            total_raw_rows += raw_chunk_len
            
            valid_chunk, chunk_dropped = validator.validate_chunk(chunk)
            
            valid_chunk_len = len(valid_chunk)
            total_valid_rows += valid_chunk_len
            
            for k in total_dropped:
                total_dropped[k] += chunk_dropped[k]
                
            stats.update(valid_chunk)
            
            # Write to intermediate parquet
            table = pa.Table.from_pandas(valid_chunk, schema=schema, preserve_index=False)
            writer.write_table(table)
            print(f"  Processed chunk {i+1} (Raw: {raw_chunk_len} -> Valid: {valid_chunk_len})")

    print("\nValidation Summary (Dropped Rows):")
    for k, v in total_dropped.items():
        print(f"  - {k}: {v}")
        
    final_stats = stats.finalize()
    print("\nDataset Statistics:")
    print(json.dumps(final_stats, indent=2))
    
    # 3. Global Orphan Check
    print("\nStep 2: Global Orphan Check...")
    # For a real dataset of 1B rows, we would only load user_id/song_id columns to check orphans,
    # or rely on the Counter from DatasetStatistics.
    # We will use the counters to report:
    users_below = sum(1 for v in stats.user_counts.values() if v < validator.min_user_interactions)
    songs_below = sum(1 for v in stats.song_counts.values() if v < validator.min_song_interactions)
    print(f"  Users below {validator.min_user_interactions} interactions: {users_below}")
    print(f"  Songs below {validator.min_song_interactions} interactions: {songs_below}")

    # 4. Temporal Splitting
    print("\nStep 3: Chronological Splitting...")
    # For huge datasets, we would group by user_id out-of-core. 
    # For this implementation we will load the intermediate parquet if it fits in memory, 
    # otherwise we'd need a multi-pass approach. 
    # We load it here to apply the Pandas split.
    print(f"  Loading {intermediate_path} into memory for temporal user-split...")
    df_full = pd.read_parquet(intermediate_path)
    
    splitter = ChronologicalSplitter(train_frac=0.8, val_frac=0.1)
    train_df, val_df, test_df = splitter.split_user_level(df_full)
    
    print(f"  Split complete:")
    print(f"  - Train: {len(train_df)} rows")
    print(f"  - Validation: {len(val_df)} rows")
    print(f"  - Test: {len(test_df)} rows")
    
    total_split_rows = len(train_df) + len(val_df) + len(test_df)
    total_dropped_rows = sum(total_dropped.values())
    
    print("\n================ INVARIANT AUDIT ================")
    print(f"Total Raw Rows:      {total_raw_rows}")
    print(f"Total Dropped Rows:  {total_dropped_rows}")
    print(f"Total Valid Rows:    {total_valid_rows}")
    print(f"Total Split Rows:    {total_split_rows}")
    
    print("\nChecks:")
    inv1 = (total_raw_rows == total_valid_rows + total_dropped_rows)
    inv2 = (total_valid_rows == total_split_rows)
    print(f"  Raw = Valid + Dropped: {'PASS' if inv1 else 'FAIL'}")
    print(f"  Valid = Train + Val + Test: {'PASS' if inv2 else 'FAIL'}")
    
    if not inv1 or not inv2:
        raise ValueError("ROW COUNT INVARIANT VIOLATED. Halting pipeline.")
    
    print("=================================================")
    
    # 5. Output
    print("\nStep 4: Writing final splits...")
    os.makedirs(output_dir, exist_ok=True)
    train_df.to_parquet(os.path.join(output_dir, "train.parquet"), index=False)
    val_df.to_parquet(os.path.join(output_dir, "validation.parquet"), index=False)
    test_df.to_parquet(os.path.join(output_dir, "test.parquet"), index=False)
    
    metadata = {
        "dataset_name": os.path.basename(filepath),
        "source": source_name,
        "source_version": "1.0",
        "download_date": datetime.utcnow().isoformat(),
        "processing_version": "v1.0",
        "statistics": final_stats,
        "split_counts": {
            "train": len(train_df),
            "validation": len(val_df),
            "test": len(test_df)
        }
    }
    
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("Done! Metadata saved to metadata.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare dataset pipeline.")
    parser.add_argument("filepath", type=str, help="Path to raw dataset.")
    parser.add_argument("--source", type=str, default="lastfm", help="Dataset source (lastfm, etc.)")
    parser.add_argument("--out", type=str, default="datasets/processed", help="Output directory")
    args = parser.parse_args()
    
    prepare_dataset(args.filepath, args.source, args.out)
