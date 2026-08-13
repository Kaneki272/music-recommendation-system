# ML Architecture Overview

## Data Flow

```mermaid
flowchart TD
    A[Raw Audio Files] --> B[Audio Extraction Pipeline
Phase 5]
    B --> C[audio_feature_vector
222 dimensions]
    C --> D[AudioFeatureVector Contract
ml/contracts/audio.py]

    E[Spotify ETL] --> F[Songs / Artists / Albums
PostgreSQL]
    F --> G[MetadataFeatureVector
ml/contracts/content.py]

    H[User Events
Kafka / MongoDB] --> I[InteractionDataset
ml/contracts/interactions.py]
    I --> J[UserItemMatrix
Collaborative Input]

    D --> K[ContentRepresentation
Multi-modal]
    G --> K

    K --> L[Content-Based Model
Phase 8]
    J --> M[Collaborative Model
Phase 9]
    F --> N[Popularity Model
Phase 7]

    L --> O[RecommendationScore]
    M --> O
    N --> O

    O --> P[ScoreNormalizer
Phase 10]
    P --> Q[CandidateSet]
    Q --> R[Hybrid Engine
Phase 10]
    R --> S[Ranker / LTR
Phase 13]
    S --> T[Final Recommendations]
```

## Module Ownership

| Contract File | Consumed By |
|---|---|
| `contracts/audio.py` | Content-Based, Feature Store |
| `contracts/content.py` | Content-Based |
| `contracts/user.py` | Collaborative, Hybrid |
| `contracts/interactions.py` | Collaborative |
| `contracts/recommendations.py` | All models |
| `contracts/candidates.py` | Hybrid Engine |
| `contracts/models.py` | Training pipeline, serving |
| `contracts/evaluation.py` | Evaluation pipeline |
