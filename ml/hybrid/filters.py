from typing import List, Set, Dict, Any

class HardFilter:
    """Removes invalid or explicitly excluded items before final ranking."""
    
    @staticmethod
    def apply(candidates: List[str], 
              exclude_song_ids: List[str],
              recently_played_song_ids: List[str],
              blocked_song_ids: List[str],
              blocked_artist_ids: List[str],  # To support this, we need song->artist mapping, assume available or skipped if not
              song_to_artist_map: Dict[str, str] = None) -> List[str]:
        """
        Filters out excluded items.
        """
        exclude_set = set(exclude_song_ids or [])
        recent_set = set(recently_played_song_ids or [])
        blocked_song_set = set(blocked_song_ids or [])
        blocked_artist_set = set(blocked_artist_ids or [])
        
        filtered_candidates = []
        for song_id in candidates:
            if song_id in exclude_set:
                continue
            if song_id in recent_set:
                continue
            if song_id in blocked_song_set:
                continue
                
            if song_to_artist_map and blocked_artist_set:
                artist_id = song_to_artist_map.get(song_id)
                if artist_id in blocked_artist_set:
                    continue
                    
            filtered_candidates.append(song_id)
            
        return filtered_candidates


class PostProcessor:
    """Applies limits (e.g. artist repetition) to scored recommendations."""
    
    @staticmethod
    def apply_artist_limit(scored_recommendations: List[Dict[str, Any]], 
                           song_to_artist_map: Dict[str, str],
                           limit: int = 2) -> List[Dict[str, Any]]:
        """
        scored_recommendations: List of dicts like {"song_id": id, "final_score": val, ...}
        Ensures no more than `limit` songs from the same artist appear.
        """
        if not song_to_artist_map or limit <= 0:
            return scored_recommendations
            
        artist_counts = {}
        final_list = []
        
        for rec in scored_recommendations:
            song_id = rec["song_id"]
            artist_id = song_to_artist_map.get(song_id, "unknown")
            
            count = artist_counts.get(artist_id, 0)
            if count < limit:
                final_list.append(rec)
                artist_counts[artist_id] = count + 1
                
        return final_list
