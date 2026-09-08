import React, { useState } from 'react';
import { sendInteraction } from '../api';

const RecommendationCard = ({ recommendation }) => {
  const [loading, setLoading] = useState(false);
  const [interactionStatus, setInteractionStatus] = useState(null);

  const handleInteraction = async (interactionType) => {
    setLoading(true);
    setInteractionStatus(null);
    try {
      await sendInteraction({
        user_id: import.meta.env.VITE_DEMO_USER_ID || "user_000949",
        song_id: recommendation.song_id,
        interaction_type: interactionType,
        timestamp: new Date().toISOString()
      });
      setInteractionStatus('success');
    } catch (err) {
      console.error(err);
      setInteractionStatus('error');
    } finally {
      setLoading(false);
      setTimeout(() => setInteractionStatus(null), 3000);
    }
  };

  return (
    <div style={{
      border: '1px solid #ccc',
      borderRadius: '8px',
      padding: '16px',
      margin: '8px 0',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      backgroundColor: '#f9f9f9'
    }}>
      <div>
        <h4 style={{ margin: '0 0 8px 0' }}>Song ID: {recommendation.song_id.substring(0, 18)}...</h4>
        <div style={{ fontSize: '14px', color: '#666' }}>
          Score: {recommendation.score.toFixed(4)} <br/>
          Model: {recommendation.model_name}
        </div>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <button 
          onClick={() => handleInteraction('play')}
          disabled={loading}
          style={{ padding: '4px 8px', cursor: 'pointer' }}
        >
          Play
        </button>
        <button 
          onClick={() => handleInteraction('like')}
          disabled={loading}
          style={{ padding: '4px 8px', cursor: 'pointer' }}
        >
          Like
        </button>
        {interactionStatus === 'success' && <span style={{ color: 'green', fontSize: '12px' }}>Sent!</span>}
        {interactionStatus === 'error' && <span style={{ color: 'red', fontSize: '12px' }}>Error</span>}
      </div>
    </div>
  );
};

export default RecommendationCard;
