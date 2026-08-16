# Dataset Ingestion Pipeline

This document outlines the architecture and execution steps for the Recommendation System Dataset Ingestion Pipeline.

## 1. Directory Structure

```text
datasets/
├── raw/            # Source files (TSV, CSV, Parquet)
├── intermediate/   # Normalised and validated Canonical Parquet chunks
└── processed/      # Split final Parquet files ready for ML (train/val/test)
```

## 2. Validation Constraints

During the chunked validation process, the following steps are performed:
- **Missing IDs:** Any row missing a `user_id` or `song_id` is dropped.
- **Timestamp Validation:** Timestamps are strictly parsed to UTC. Any timestamp in the future or before 1970 is dropped.
- **Interaction Types:** Only known canonical interaction types (e.g. `play`, `like`, `skip`) are allowed. The Last.fm adapter natively maps all interactions to `play`. No types are fabricated.
- **Exact Duplicates:** Duplicates are defined as identical rows across `[user_id, song_id, interaction_type, timestamp, source]`. Two plays of the same song by the same user at *different* timestamps are considered distinct interactions and are preserved.

## 3. Chronological Evaluation Strategy

To prevent temporal leakage, the dataset is split temporally on a per-user basis (80% train, 10% val, 10% test).

- The dataset is globally sorted by `user_id` and `timestamp`.
- For each user, their chronological history is ranked as percentiles.
- The first 80% of interactions become the `train` set.
- The next 10% become the `validation` set.
- The final 10% become the `test` set.

**Handling Cold-Start Users:**
Users who only appear in the validation or test sets are explicitly preserved. The evaluation system is responsible for handling them as pure cold-start scenarios, rather than silently leaking their information or dropping them.

## 4. How to Import a Real Last.fm Dataset

If you have a large dataset like LFM-1b (1 billion scrobbles), follow these exact steps to run it through the memory-safe ingestion pipeline.

1. **Place the raw TSV in the datasets folder:**
   ```bash
   cp /path/to/LFM-1b_le.txt datasets/raw/lastfm.tsv
   ```

2. **Inspect the dataset:**
   Verify the schema matches the adapter expectations.
   ```bash
   python scripts/inspect_dataset.py datasets/raw/lastfm.tsv
   ```

3. **Validate the dataset (Optional dry-run):**
   Runs chunked validation and computes statistics without saving the heavy Parquet outputs.
   ```bash
   python scripts/validate_dataset.py datasets/raw/lastfm.tsv --source lastfm
   ```

4. **Prepare the dataset:**
   Runs chunked validation, applies chronological splitting, generates `metadata.json`, and writes `train.parquet`, `validation.parquet`, and `test.parquet`.
   ```bash
   python scripts/prepare_dataset.py datasets/raw/lastfm.tsv --source lastfm --out datasets/processed/lastfm
   ```

5. **Review Output:**
   Inspect `datasets/processed/lastfm/metadata.json` for calculated sparsity, user/song interaction distribution (min, max, median, mean), and memory constraints.
