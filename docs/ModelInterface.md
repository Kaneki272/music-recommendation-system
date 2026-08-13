# Recommendation Model Interface

## RecommendationModelInterface

Every model (Popularity, Content-Based, Collaborative, Hybrid, Ranking)
MUST implement `ml/interfaces/recommendation_model.py`.

```python
class MyModel(RecommendationModelInterface):
    async def train(dataset_version, **kwargs) -> ModelMetadata
    async def predict(request: RecommendationRequest) -> RecommendationResponse
    async def save(artifact_path: str) -> None
    async def load(artifact_path: str) -> None
    def get_metadata() -> ModelMetadata
    def is_ready() -> bool
```

## Score Normalization Rule
Raw scores from different models are NOT comparable.
The Hybrid Engine always calls `ScoreNormalizerInterface.normalize()`
before blending scores from different models.

## Model Artifact Structure
```
models/
  content_based/
    v1/
      model/         ← weights
      config.yaml    ← hyperparameters
      metadata.json  ← ModelMetadata serialized
    v2/              ← old versions NEVER deleted
  collaborative/
    v1/
  popularity/
    v1/
```
