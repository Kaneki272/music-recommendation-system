import { apiClient } from './client';

export interface ArtistResponse {
  id: string;
  name: string;
  bio?: string;
  image_url?: string;
}

export interface AlbumResponse {
  id: string;
  title: string;
  artist_id: string;
  release_date?: string;
  cover_image_url?: string;
}

export interface TrackResponse {
  id: string;
  title: string;
  artist?: ArtistResponse;
  album?: AlbumResponse;
  duration_ms: number;
  genres?: string[];
  audio_url?: string;
  match_score?: number;
  recommendation_reason?: string;
}

export const getRecommendations = async (userId: string, limit: number = 10): Promise<TrackResponse[]> => {
  const response = await apiClient.get<any>(`/api/v1/recommendations/`, {
    params: {
      user_id: userId,
      limit,
    },
  });
  
  return response.data.recommendations.map((rec: any) => ({
    id: rec.song_id,
    title: rec.metadata?.title || 'Unknown Title',
    artist: { id: '', name: rec.metadata?.artist || 'Unknown Artist' },
    duration_ms: 0,
    audio_url: rec.metadata?.audio_url,
    match_score: rec.score,
    recommendation_reason: `Match: ${(rec.score * 100).toFixed(0)}%`,
  }));
};
