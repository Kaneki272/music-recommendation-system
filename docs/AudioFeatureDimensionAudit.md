# Audio Feature Dimension Audit (Phase 11A)

## 1. Expected Dimension
**222 dimensions**
This was the expected and documented size of the `audio_feature_vector` in:
- `ml/contracts/identifiers.py` (`CANONICAL_VECTOR_DIMENSION = 222`)
- `ml/contracts/audio.py` (Docstring and `feature_dimension` validator)
- `backend/database/qdrant/client.py`
- End-to-end tests and extraction demo scripts.

## 2. Actual Dimension
**215 dimensions**
Observed across all tested real audio files (both MP3s and synthesized WAV files).

## 3. Root Cause
The root cause is a mathematical miscalculation in the original architectural specification (`features/audio/aggregator.py` docstring), not an error in the extraction implementation. The `audio_feature_vector` concatenates fixed statistical moments (mean, std, min, max, median, skewness, kurtosis) across various time-series features. When summing these component dimensions correctly, the result is exactly 215, not 222. The implementation correctly produces 215 dimensions, but the contract incorrectly demanded 222.

## 4. Feature-by-Feature Dimension Accounting

| Feature Family | Sub-Feature | Calculation | Output Dimensions |
| :--- | :--- | :--- | :--- |
| **Rhythm** | Tempo (BPM) | 1 global estimate | 1 |
| | Beat Count | 1 global count | 1 |
| | Onset Strength | 1 stat (mean) | 1 |
| **Timbral** | MFCC | 20 coefficients × 7 stats | 140 |
| | Spectral Centroid | 1 band × 7 stats | 7 |
| | Spectral Rolloff | 1 band × 7 stats | 7 |
| | Spectral Bandwidth | 1 band × 7 stats | 7 |
| | Zero Crossing Rate | 1 band × 7 stats | 7 |
| | RMS Energy | 1 band × 7 stats | 7 |
| **Harmonic** | Chroma STFT | 12 pitch classes × 2 stats (mean, std) | 24 |
| | Tonnetz | 6 dimensions × 2 stats (mean, std) | 12 |
| | Harmonic Ratio | 1 global ratio | 1 |
| **TOTAL** | | | **215** |

The mathematical sum of the designed features is precisely **215**. 

## 5. Files Affected
To synchronize the codebase to the mathematically correct dimension of 215, the following files must be updated:
- `ml/contracts/identifiers.py` (Update `CANONICAL_VECTOR_DIMENSION = 215`)
- `ml/contracts/audio.py` (Update docstring and JSON schema example)
- `features/audio/aggregator.py` (Update docstring)
- `backend/database/qdrant/client.py` (Update docstring)
- `scripts/demo_feature_extraction.py` (Update assertion and prints)
- `scripts/run_e2e_feature_pipeline.py` (Update validation prints)
- `scripts/run_extraction_demo.py` (Update validation prints)
- `tests/ml/test_contracts.py` (Update tests from 222 to 215)
- `docs/AudioFeatures.md`, `docs/ContentBasedModel.md`, `docs/MLArchitecture.md`, `docs/MLDataContracts.md` (Update documentation)

## 6. Corrective Action
**Proposed Action:** Adopt 215 as the canonical dimension. 
The rule explicitly prohibits padding or generating synthetic values to reach 222. We must align the contracts, Qdrant collection, and tests with the mathematical reality of 215 dimensions.

## 7. Tests (Regression Plan)
We need to add/update tests in `tests/ml/test_contracts.py` and potentially a new `tests/features/test_extraction_regression.py` to assert:
- `len(vector) == 215` for all extracted vectors.
- No `NaN` or `inf` values in the extracted vectors.
- Deterministic extraction (repeated extraction yields the same vector).
- Qdrant client initializes the collection with exactly 215 dimensions.

## 8. Qdrant Compatibility
**Migration Plan:**
Currently, Qdrant is initialized via `backend/database/qdrant/client.py` which reads `CANONICAL_VECTOR_DIMENSION` (currently 222). 
Because the dimension of a Qdrant collection is immutable once created, if a collection named `audio_v1` was already created with dimension 222 during testing, inserts of 215-dimensional vectors will fail. 
We must either:
1. Delete the existing `audio_v1` collection and recreate it with dimension 215 (since this is still a testing phase).
2. Or bump the collection name to `audio_v2` and start fresh.

*Recommendation: Since we are in the development/validation phase and haven't populated a production database, we can recreate the collection or bump to `audio_v2`.*

## 9. Final Verified Dimension
**215**

---
**STATUS: BLOCKED**
Awaiting project owner approval to implement the Corrective Action (changing canonical contract to 215 and applying Qdrant migration plan).
