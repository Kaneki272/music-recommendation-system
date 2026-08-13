"""
Metadata Similarity Scorers
===========================
Calculates similarity scores for non-audio modalities.
"""
from typing import List, Optional
from ml.contracts.content import MetadataFeatureVector


def calculate_genre_similarity(user_genres: List[str], candidate_genres: List[str]) -> float:
    """
    Jaccard-like similarity for genres. 
    Score between 0.0 and 1.0.
    """
    if not user_genres or not candidate_genres:
        return 0.0
        
    set_user = set(user_genres)
    set_cand = set(candidate_genres)
    
    intersection = set_user.intersection(set_cand)
    # Using modified Jaccard - dividing by candidate length gives higher score 
    # if the candidate perfectly fits inside user's broad taste.
    return len(intersection) / len(set_cand) if set_cand else 0.0


def calculate_artist_similarity(user_artists: List[str], candidate_artist_popularity: Optional[float]) -> float:
    """
    Simplified placeholder. In a full system, candidate would have artist IDs.
    For this v1, we use artist_popularity as a proxy if explicit artist matching isn't possible.
    """
    # Assuming candidate_artist_popularity is [0, 100]
    if candidate_artist_popularity is None:
        return 0.0
    return candidate_artist_popularity / 100.0


def calculate_metadata_boost(
    user_genres: List[str],
    user_artists: List[str],
    candidate_metadata: Optional[MetadataFeatureVector],
    genre_weight: float,
    artist_weight: float
) -> float:
    """Computes the weighted sum of metadata similarities."""
    if not candidate_metadata:
        return 0.0
        
    genre_sim = calculate_genre_similarity(user_genres, candidate_metadata.genres)
    artist_sim = calculate_artist_similarity(user_artists, candidate_metadata.artist_popularity)
    
    return (genre_sim * genre_weight) + (artist_sim * artist_weight)
