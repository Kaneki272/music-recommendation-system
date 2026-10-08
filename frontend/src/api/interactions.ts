import { apiClient } from './client';

export interface InteractionEvent {
  user_id: string;
  song_id: string;
  interaction_type: string;
  timestamp: string;
  weight?: number;
  duration_played_ms?: number;
  completion_rate?: number;
  session_id?: string;
}

export const postInteraction = async (payload: Omit<InteractionEvent, 'timestamp'>): Promise<any> => {
  const fullPayload: InteractionEvent = {
    ...payload,
    timestamp: new Date().toISOString(),
  };
  const response = await apiClient.post('/api/v1/interactions/', fullPayload);
  return response.data;
};
