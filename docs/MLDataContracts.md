# ML Data Contracts

## Canonical Identifier Rules

| Identifier | Type | Storage | ML Usage |
|---|---|---|---|
| `song_id` | Internal UUID | PostgreSQL `songs.id` | ✅ PRIMARY — use everywhere |
| `user_id` | Internal UUID | PostgreSQL `users.id` | ✅ PRIMARY — use everywhere |
| `spotify_track_id` | External string | `songs.spotify_id` | ❌ ETL layer only |
| `artist_id` | Internal UUID | PostgreSQL `artists.id` | ✅ Secondary reference |
| `session_id` | Ephemeral UUID | Not persisted | ✅ Session context only |

## Audio Feature Vector (222 Dimensions)

| Index Range | Feature | Stats |
|---|---|---|
| 0 | tempo_bpm | raw scalar |
| 1 | beat_count | raw scalar |
| 2 | onset_strength_mean | raw scalar |
| 3–142 | mfcc_[0–19] | ×7 stats each |
| 143–149 | spectral_centroid | ×7 stats |
| 150–156 | spectral_rolloff | ×7 stats |
| 157–163 | spectral_bandwidth | ×7 stats |
| 164–170 | zero_crossing_rate | ×7 stats |
| 171–177 | rms_energy | ×7 stats |
| 178–201 | chroma_stft_[0–11] | ×2 stats each |
| 202–213 | tonnetz_[0–5] | ×2 stats each |
| 214 | harmonic_ratio | raw scalar |

## Interaction Weights (configurable)

Load from `config/ml_config.yaml`. Never hardcode.

| Interaction | Default Weight |
|---|---|
| play | 1.0 |
| complete | 2.0 |
| like | 4.0 |
| playlist_add | 3.0 |
| share | 3.5 |
| skip | -1.0 |
| skip_early | -2.0 |
