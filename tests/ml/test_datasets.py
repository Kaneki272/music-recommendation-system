import pytest
import pandas as pd
import json
import os
from datetime import datetime
from ml.datasets.validator import DatasetValidator
from ml.datasets.splitter import ChronologicalSplitter
from ml.datasets.stats import DatasetStatistics
from ml.datasets.adapters import DatasetAdapter

def test_validator_duplicates_and_timestamps():
    validator = DatasetValidator()
    
    # Create mock chunk
    data = [
        {"user_id": "u1", "song_id": "s1", "interaction_type": "play", "timestamp": "2026-01-01T12:00:00Z", "weight": 1.0, "source": "test"},
        {"user_id": "u1", "song_id": "s1", "interaction_type": "play", "timestamp": "2026-01-01T12:00:00Z", "weight": 1.0, "source": "test"}, # Exact dup
        {"user_id": "u1", "song_id": "s1", "interaction_type": "play", "timestamp": "2026-01-02T12:00:00Z", "weight": 1.0, "source": "test"}, # Not a dup, diff time
        {"user_id": "u2", "song_id": "s2", "interaction_type": "play", "timestamp": "1960-01-01T12:00:00Z", "weight": 1.0, "source": "test"}, # Invalid time
        {"user_id": "u3", "song_id": "s3", "interaction_type": "fabrication", "timestamp": "2026-01-01T12:00:00Z", "weight": 1.0, "source": "test"}, # Invalid type
        {"user_id": "u4", "song_id": None, "interaction_type": "play", "timestamp": "2026-01-01T12:00:00Z", "weight": 1.0, "source": "test"}, # Missing id
    ]
    df = pd.DataFrame(data)
    
    valid_df, dropped = validator.validate_chunk(df)
    
    assert len(valid_df) == 2
    assert dropped["exact_duplicates"] == 1
    assert dropped["invalid_timestamp"] == 1
    assert dropped["invalid_type"] == 1
    assert dropped["missing_ids"] == 1

def test_chronological_splitting():
    splitter = ChronologicalSplitter(train_frac=0.6, val_frac=0.2)
    
    # 1 user, 10 interactions across time
    dates = pd.date_range(start="2026-01-01", periods=10, freq="D")
    data = [{"user_id": "u1", "song_id": f"s{i}", "timestamp": d} for i, d in enumerate(dates)]
    df = pd.DataFrame(data)
    
    train, val, test = splitter.split_user_level(df)
    
    # 60% of 10 = 6, 20% = 2, 20% = 2
    assert len(train) == 6
    assert len(val) == 2
    assert len(test) == 2
    
    # Test strict chronology
    assert train['timestamp'].max() < val['timestamp'].min()
    assert val['timestamp'].max() < test['timestamp'].min()

def test_incremental_stats():
    stats = DatasetStatistics()
    
    # 2 chunks
    chunk1 = pd.DataFrame([
        {"user_id": "u1", "song_id": "s1", "timestamp": pd.Timestamp("2026-01-01")},
        {"user_id": "u1", "song_id": "s2", "timestamp": pd.Timestamp("2026-01-02")}
    ])
    chunk2 = pd.DataFrame([
        {"user_id": "u2", "song_id": "s1", "timestamp": pd.Timestamp("2026-01-03")},
        {"user_id": "u3", "song_id": "s3", "timestamp": pd.Timestamp("2026-01-04")}
    ])
    
    stats.update(chunk1)
    stats.update(chunk2)
    
    res = stats.finalize()
    assert res["total_interactions"] == 4
    assert res["unique_users"] == 3
    assert res["unique_songs"] == 3
    
    # interactions per user: u1=2, u2=1, u3=1
    assert res["interactions_per_user"]["max"] == 2
    assert res["interactions_per_user"]["min"] == 1
    
    # time bounds
    assert res["time_range_start"] == pd.Timestamp("2026-01-01").isoformat()
    assert res["time_range_end"] == pd.Timestamp("2026-01-04").isoformat()

def test_leakage_and_invariants():
    splitter = ChronologicalSplitter(train_frac=0.8, val_frac=0.1)
    
    # 2 users, multiple interactions
    dates = pd.date_range(start="2026-01-01", periods=10, freq="D")
    data = [{"user_id": "u1", "song_id": f"s{i}", "timestamp": d} for i, d in enumerate(dates)]
    data += [{"user_id": "u2", "song_id": f"s{i}", "timestamp": d} for i, d in enumerate(dates)]
    
    df = pd.DataFrame(data)
    initial_rows = len(df)
    
    train, val, test = splitter.split_user_level(df)
    
    # Invariant: valid_rows = train_rows + validation_rows + test_rows
    assert len(train) + len(val) + len(test) == initial_rows
    
    # Check no overlap of exact interaction indices (if we keep indices) or row data
    # We can just check that the total sum of rows is exact and no interaction is duplicated
    assert len(train.merge(val, on=["user_id", "timestamp"])) == 0
    assert len(train.merge(test, on=["user_id", "timestamp"])) == 0
    assert len(val.merge(test, on=["user_id", "timestamp"])) == 0
    
    # User u1 should have 8 train, 1 val, 1 test
    u1_train = train[train['user_id'] == 'u1']
    u1_val = val[val['user_id'] == 'u1']
    u1_test = test[test['user_id'] == 'u1']
    
    # Temporal leakage checks
    assert u1_train['timestamp'].max() < u1_val['timestamp'].min()
    assert u1_val['timestamp'].max() < u1_test['timestamp'].min()
