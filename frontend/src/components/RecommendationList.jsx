import React, { useState, useEffect } from 'react';
import { getRecommendations } from '../api';
import RecommendationCard from './RecommendationCard';

const RecommendationList = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const userId = import.meta.env.VITE_DEMO_USER_ID || "user_000949";

  const fetchRecs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRecommendations(userId, 10);
      setRecommendations(data.recommendations || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecs();
  }, []);

  if (loading) return <div>Loading recommendations...</div>;
  if (error) return <div style={{ color: 'red' }}>Error: {error}</div>;
  if (recommendations.length === 0) return <div>No recommendations found.</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>For You (User: {userId})</h3>
        <button onClick={fetchRecs} style={{ padding: '4px 8px' }}>Refresh</button>
      </div>
      <div style={{ marginTop: '16px' }}>
        {recommendations.map(rec => (
          <RecommendationCard key={rec.song_id} recommendation={rec} />
        ))}
      </div>
    </div>
  );
};

export default RecommendationList;
