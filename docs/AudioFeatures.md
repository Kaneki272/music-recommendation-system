# Audio Feature Extraction Architecture

## Pipeline Flow

```
AudioSource (URI)
      ↓
[5.1] AudioFetcher       — Download/stream raw audio bytes
      ↓
[5.2] AudioPreprocessor  — Mono, 22.05 kHz, silence trim
      ↓
[5.3] DSPExtractor       — Librosa: Rhythm + Timbral + Harmonic
      ↓
[5.4] FeatureAggregator  — Time-series → Fixed 222-dim vector
      ↓
AudioFeatureVector       — Persisted to PostgreSQL + Qdrant
```

## Feature Vector Breakdown (222 dimensions)

| Feature Group | Raw Shape | Stats | Dimensions |
|---|---|---|---|
| Tempo BPM | scalar | raw | 1 |
| Beat Count | scalar | raw | 1 |
| Onset Strength Mean | scalar | raw | 1 |
| MFCC | (20, T) | mean, std, min, max, median, skew, kurt | 140 |
| Spectral Centroid | (1, T) | × 7 stats | 7 |
| Spectral Rolloff | (1, T) | × 7 stats | 7 |
| Spectral Bandwidth | (1, T) | × 7 stats | 7 |
| Zero Crossing Rate | (1, T) | × 7 stats | 7 |
| RMS Energy | (1, T) | × 7 stats | 7 |
| Chroma STFT | (12, T) | mean, std | 24 |
| Tonnetz | (6, T) | mean, std | 12 |
| Harmonic Ratio | scalar | raw | 1 |
| **Total** | | | **222** |

## Supported Audio Sources

| Source Type | Example | Notes |
|---|---|---|
| `HTTP_URL` | Spotify 30s preview URL | Default for Spotify ETL integration |
| `LOCAL_FILE` | `/storage/raw/tracks/song.mp3` | For locally stored audio |
| `S3_URI` | `s3://bucket/tracks/song.mp3` | Future cloud audio storage |

## Extraction Versioning
Every `AudioFeature` row stores an `extraction_version` string (e.g., `v1.0.0`).
When the Librosa pipeline changes, all old records can be reprocessed by filtering
`WHERE extraction_version != current_version` — without touching any other data.
