import os
import json
from datetime import datetime
from pydantic import BaseModel

class ArtifactManager:
    """Manages the saving and loading of CF model artifacts conforming to ModelMetadata."""
    
    @staticmethod
    def save_metadata(path: str, metadata: dict):
        os.makedirs(path, exist_ok=True)
        # Add required ModelMetadata fields
        metadata['model_name'] = "CollaborativeFiltering_ALS"
        metadata['model_type'] = "collaborative"
        metadata['artifact_path'] = path
        metadata['is_production'] = False
        
        # Serialize datetime if any
        for k, v in metadata.items():
            if isinstance(v, datetime):
                metadata[k] = v.isoformat()
                
        with open(os.path.join(path, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
