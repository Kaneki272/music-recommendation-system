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
  const response = await apiClient.get<TrackResponse[]>(`/api/v1/recommendations/user/${userId}`, {
    params: {
      limit,
    },
  });
  return response.data;
};
