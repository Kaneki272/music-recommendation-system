import React, { useEffect, useState } from 'react';
import { getHealth, isMockMode } from './api';
import RecommendationList from './components/RecommendationList';

function App() {
  const [health, setHealth] = useState(null);
  
  useEffect(() => {
    getHealth().then(setHealth).catch(err => setHealth({ error: err.message }));
  }, []);

  const modeBadgeStyle = {
    padding: '4px 8px',
    borderRadius: '4px',
    fontWeight: 'bold',
    backgroundColor: isMockMode() ? '#ffd700' : '#4caf50',
    color: isMockMode() ? '#000' : '#fff',
    display: 'inline-block',
    marginBottom: '16px'
  };

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '24px', fontFamily: 'sans-serif' }}>
      <header style={{ borderBottom: '1px solid #eee', paddingBottom: '16px', marginBottom: '24px' }}>
        <h1 style={{ margin: '0 0 16px 0' }}>Music RecSys</h1>
        <div style={modeBadgeStyle}>
          {isMockMode() ? 'MOCK MODE' : 'API MODE'}
        </div>
        <div style={{ fontSize: '12px', color: '#666' }}>
          Backend Status: {health ? (health.error ? <span style={{ color: 'red' }}>{health.error}</span> : <span style={{ color: 'green' }}>Reachable</span>) : 'Checking...'}
        </div>
      </header>
      
      <main>
        <RecommendationList />
      </main>
    </div>
  );
}

export default App;
