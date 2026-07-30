# ETL Ingestion Pipeline Architecture

This document defines the strict sequential flow of data from external sources (like Spotify) through our extraction, transformation, and loading (ETL) pipeline into our core databases.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant Scheduler
    participant Client as Spotify Client
    participant RateLimiter as Rate Limiter
    participant RawStorage as Raw Storage
    participant Validator
    participant Normalizer
    participant Deduplicator
    participant Loader
    participant DB as MongoDB/PostgreSQL

    Scheduler->>Client: Trigger Sync Job
    Client->>RateLimiter: Check Quota
    RateLimiter-->>Client: Allowed
    Client->>Client: Fetch Data
    Client->>RawStorage: Save Raw JSON
    RawStorage->>Validator: Validate Schema
    Validator->>Normalizer: Map to Internal Models
    Normalizer->>Deduplicator: Check Existing Records
    Deduplicator->>Loader: Pass Unique Records
    Loader->>DB: Bulk Insert/Upsert
```
