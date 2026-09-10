import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/useAuthStore';

export function Auth() {
  const [username, setUsername] = useState('');
  const login = useAuthStore(state => state.login);
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username.trim()) {
      login(username.trim());
      navigate('/home');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md p-8 glass-panel rounded-2xl space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold">Sign In</h2>
          <p className="text-muted-foreground mt-2">Enter any username to start discovering.</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">User ID</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-input border border-border rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary text-foreground placeholder:text-muted-foreground"
              placeholder="e.g. user_123"
              required
            />
          </div>
          
          <button 
            type="submit"
            className="w-full bg-primary text-primary-foreground font-bold py-3 rounded-lg hover:bg-primary/90 transition-colors"
          >
            Continue
          </button>
        </form>
      </div>
    </div>
  );
}
