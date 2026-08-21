from typing import Dict, Any

class HybridConfig:
    # User state definitions based on training interactions
    NEW_USER_THRESHOLD = 0
    SPARSE_USER_MAX = 4

    # Experimental default weights (ALS, Content, Popularity)
    # These map to: [w_ALS, w_Content, w_Pop]
    WEIGHTS_KNOWN_USER = {"als": 0.60, "content": 0.00, "popularity": 0.40}
    WEIGHTS_SPARSE_USER = {"als": 0.30, "content": 0.00, "popularity": 0.70}
    WEIGHTS_NEW_USER = {"als": 0.00, "content": 0.00, "popularity": 1.00}

    # Weight config with content available (not active unless content is truly available)
    WEIGHTS_KNOWN_USER_WITH_CONTENT = {"als": 0.60, "content": 0.25, "popularity": 0.15}
    WEIGHTS_SPARSE_USER_WITH_CONTENT = {"als": 0.30, "content": 0.30, "popularity": 0.40}

    # Post-processing configurations
    ARTIST_REPETITION_LIMIT = 2
    ALBUM_REPETITION_LIMIT = 2  # Optional, if album info exists

    @classmethod
    def get_base_weights(cls, user_interactions: int, content_available: bool = False) -> Dict[str, float]:
        """Returns the appropriate raw weights based on user state and content availability."""
        if user_interactions == cls.NEW_USER_THRESHOLD:
            return cls.WEIGHTS_NEW_USER.copy()
        elif user_interactions <= cls.SPARSE_USER_MAX:
            return cls.WEIGHTS_SPARSE_USER_WITH_CONTENT.copy() if content_available else cls.WEIGHTS_SPARSE_USER.copy()
        else:
            return cls.WEIGHTS_KNOWN_USER_WITH_CONTENT.copy() if content_available else cls.WEIGHTS_KNOWN_USER.copy()
