import { apiClient } from './client';

export interface InteractionEvent {
  user_id: string;
  song_id: string;
  interaction_type: string;
  timestamp: string;
  weight?: number;
}

export const postInteraction = async (payload: Omit<InteractionEvent, 'timestamp'>): Promise<any> => {
  const fullPayload: InteractionEvent = {
    ...payload,
    timestamp: new Date().toISOString(),
  };
  const response = await apiClient.post('/api/v1/analytics/interaction', fullPayload);
  return response.data;
};
