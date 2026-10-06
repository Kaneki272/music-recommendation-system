import { apiClient } from './client';

export interface SongItem {
  song_id: string;
  title: string;
  artist: string;
  filename: string;
  audio_url: string;
  has_audio: boolean;
}

export interface SongsResponse {
  total: number;
  limit: number;
  offset: number;
  songs: SongItem[];
}

export const getSongs = async (limit: number = 50, offset: number = 0): Promise<SongsResponse> => {
  const response = await apiClient.get<SongsResponse>('/api/v1/songs/', {
    params: { limit, offset }
  });
  return response.data;
};

export interface SuggestedSong {
  song_id: string;
  title: string;
  artist: string;
  similarity_score: number;
  audio_url: string;
}

export interface SuggestionResponse {
  target_song_id: string;
  target_song_title: string;
  target_artist: string;
  match_algorithm: string;
  suggested_songs: SuggestedSong[];
}

export const getSimilarSongs = async (songId: string, limit: number = 10, userId?: string): Promise<SuggestionResponse> => {
  const response = await apiClient.get<SuggestionResponse>(`/api/v1/songs/${songId}/similar`, {
    params: { limit, user_id: userId }
  });
  return response.data;
};
