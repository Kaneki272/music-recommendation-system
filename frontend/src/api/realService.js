const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const getRealRecommendations = async (userId, limit) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/recommendations/?user_id=${encodeURIComponent(userId)}&limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Real API Error: ${response.status} ${response.statusText}`);
  }
  return response.json();
};

export const sendRealInteraction = async (interaction) => {
  const response = await fetch(`${API_BASE_URL}/api/v1/interactions/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(interaction)
  });
  if (!response.ok) {
    throw new Error(`Real API Error: ${response.status} ${response.statusText}`);
  }
  return response.json();
};

export const getRealHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Real API Error: ${response.status} ${response.statusText}`);
  }
  return response.json();
};
