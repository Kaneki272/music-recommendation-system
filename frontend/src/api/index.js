import { getMockRecommendations, sendMockInteraction, getMockHealth } from './mockService';
import { getRealRecommendations, sendRealInteraction, getRealHealth } from './realService';

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === 'true';

export const getRecommendations = async (userId, limit = 10) => {
  if (USE_MOCK) {
    return getMockRecommendations(userId, limit);
  }
  return getRealRecommendations(userId, limit);
};

export const sendInteraction = async (interaction) => {
  if (USE_MOCK) {
    return sendMockInteraction(interaction);
  }
  return sendRealInteraction(interaction);
};

export const getHealth = async () => {
  if (USE_MOCK) {
    return getMockHealth();
  }
  return getRealHealth();
};

export const isMockMode = () => USE_MOCK;
