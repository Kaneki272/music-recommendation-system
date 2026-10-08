import { Routes, Route, Navigate } from 'react-router-dom';
import { Shell } from '@/components/layout/Shell';
import { Landing } from '@/pages/Landing';
import { Auth } from '@/pages/Auth';
import { Home } from '@/pages/Home';
import { useAuthStore } from '@/stores/useAuthStore';

import { Search } from '@/pages/Search';
import { Discover } from '@/pages/Discover';

// Protected Route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);

  return (
    <Routes>
      <Route path="/" element={isAuthenticated ? <Navigate to="/home" replace /> : <Landing />} />
      <Route path="/auth" element={<Auth />} />
      
      {/* Protected App Shell Routes */}
      <Route path="/" element={<ProtectedRoute><Shell /></ProtectedRoute>}>
        <Route path="home" element={<Home />} />
        <Route path="discover" element={<Discover />} />
        <Route path="search" element={<Search />} />
        <Route path="library" element={<div className="p-4 text-muted-foreground">Library (Coming Soon)</div>} />
        <Route path="settings" element={<div className="p-4 text-muted-foreground">Settings</div>} />
      </Route>
    </Routes>
  );
}
