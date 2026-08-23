# Audio Feature Dimension Migration (Phase 11A)

## 1. Why 222 was incorrect
The original architecture incorrectly documented the audio feature vector dimension as `222`. This was due to an arithmetic miscalculation when summing the expected dimensions of the extracted components in `features/audio/aggregator.py`. The actual underlying Librosa-based extraction logic was producing the correct components, but the total dimension specified by the contract in `ml/contracts/identifiers.py` and downstream tests mathematically contradicted the sum of its parts.

## 2. Why 215 is correct
The extraction pipeline comprises the following features aggregated into statistical moments. When summed correctly, the actual output is `215`. The extraction pipeline code was working exactly as designed; only the contract and tests needed to be aligned with this mathematical reality.

## 3. Dimension Breakdown
| Feature Family | Sub-Feature | Dimensions |
| :--- | :--- | :--- |
| **Rhythm** | Tempo (BPM), Beat Count, Onset Strength | 3 |
| **Timbral** | MFCC (20 coefficients × 7 stats) | 140 |
| | Spectral Centroid (1 band × 7 stats) | 7 |
| | Spectral Rolloff (1 band × 7 stats) | 7 |
| | Spectral Bandwidth (1 band × 7 stats) | 7 |
| | Zero Crossing Rate (1 band × 7 stats) | 7 |
| | RMS Energy (1 band × 7 stats) | 7 |
| **Harmonic** | Chroma STFT (12 pitch classes × 2 stats) | 24 |
| | Tonnetz (6 dimensions × 2 stats) | 12 |
| | Harmonic Ratio | 1 |
| **TOTAL** | | **215** |

## 4. Old `audio_v1` Architecture
- Expected Dimension: `222`
- Qdrant Collection: `audio_v1` (with `size=222`)
- This version is deprecated but preserved for legacy compatibility checks. Any new 215-D vectors pushed to `audio_v1` will correctly raise a `ValueError` by the Qdrant client or be rejected by the Qdrant database.

## 5. New `audio_v2` Architecture
- Expected Dimension: `215` (The mathematically correct, canonical dimension)
- Qdrant Collection: `audio_v2` (Configurable via `QDRANT_AUDIO_COLLECTION`)
- `CANONICAL_VECTOR_DIMENSION = 215`

## 6. Migration Strategy
Instead of deleting `audio_v1` or padding vectors with synthetic values to reach 222 (which violates the invariant rules against data fabrication), we bumped the extraction version and target Qdrant collection to `audio_v2`.
- Qdrant initialization points to `audio_v2`.
- The `QdrantVectorStore` defaults to `audio_v2` but is configurable.
- Existing 222-D vectors must NOT be migrated. Existing audio files should be re-extracted with the updated pipeline to generate valid 215-D vectors for `audio_v2`.

## 7. Extraction Versioning
- **Vector Dimension:** `215`
- **Extraction Version:** `audio_v2`
Every stored vector retains the `song_id`, `extraction_version`, `vector_dimension`, and `tempo_bpm`/`harmonic_ratio` as payload metadata. This guarantees safe filtering and future-proofs the model.

## 8. Compatibility Rules
- `audio_v1` ONLY accepts 222-D vectors (Legacy).
- `audio_v2` ONLY accepts 215-D vectors (Current).
- Content-Based models and Feast feature stores should now expect the 215-D vector length.

## 9. Test Results
The regression test suite (`tests/features/test_extraction_regression.py`) successfully asserts:
1. Exact dimension = 215.
2. No NaN values.
3. No infinite values.
4. Deterministic extraction logic.
5. Qdrant `audio_v1` rejects 215-D inputs.
6. Qdrant `audio_v2` accepts 215-D inputs and preserves schema metadata.
