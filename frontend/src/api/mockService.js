export const getMockRecommendations = async (userId, limit) => {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 800));
  
  const recommendations = [];
  for (let i = 0; i < limit; i++) {
    recommendations.push({
      song_id: `mbid:mock-${Math.floor(Math.random() * 100000)}-${i}`,
      score: 0.99 - (i * 0.05),
      model_name: "hybrid",
      model_version: "v1.0.0",
      rank: i + 1,
      metadata: { mock: true },
      generated_at: new Date().toISOString()
    });
  }

  return {
    user_id: userId,
    recommendations,
    model_name: "hybrid",
    model_version: "v1.0.0",
    generated_at: new Date().toISOString(),
    latency_ms: 800,
    metadata: { user_state: "KNOWN_USER", is_mock: true }
  };
};

export const sendMockInteraction = async (interaction) => {
  await new Promise(resolve => setTimeout(resolve, 300));
  console.log("[MOCK API] Interaction sent:", interaction);
  return { status: "ok", mock: true };
};

export const getMockHealth = async () => {
  await new Promise(resolve => setTimeout(resolve, 200));
  return { status: "ok", app: "Mock API (Music Recommendation)" };
};
