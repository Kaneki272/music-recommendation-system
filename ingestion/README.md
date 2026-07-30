# ETL Pipeline Architectural Guarantees

Any implementation within this module MUST adhere to the following 5 principles:

## 1. Idempotency (⭐⭐⭐⭐⭐)
- Running the ETL twice on the same data must not create duplicates.
- The `LoaderInterface` strictly enforces `bulk_upsert` behavior utilizing ON CONFLICT (Postgres) or upsert (Mongo).

## 2. Incremental Sync (⭐⭐⭐⭐⭐)
- Do not fetch the full catalog. 
- Use `SyncStateManagerInterface` to persist and retrieve the `last_cursor` or `last_sync_time`, fetching only delta updates.

## 3. Batch Processing (⭐⭐⭐⭐)
- The `LoaderInterface.bulk_upsert` must chunk data (e.g., 100-record batches). Never insert one record at a time.

## 4. Retry Strategy (⭐⭐⭐⭐)
- All external calls in `spotify_fetcher` must be wrapped with the `with_exponential_backoff` decorator (defined in `retry_strategy.py`).
- Handled codes: 429 (Rate Limit), 500, 502, 503, and Timeouts.

## 5. Structured Logging (⭐⭐⭐⭐)
- Every job must emit structured trace logs: `Started -> Extracted -> Validated -> Normalized -> Loaded -> Completed`.
- Managed via `job_tracker.py` and `logger.py`.
