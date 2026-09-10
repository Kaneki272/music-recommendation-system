import { Routes, Route, Navigate } from 'react-router-dom';
import { Shell } from '@/components/layout/Shell';
import { Landing } from '@/pages/Landing';
import { Auth } from '@/pages/Auth';
import { Home } from '@/pages/Home';
import { useAuthStore } from '@/stores/useAuthStore';

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
        <Route path="discover" element={<div className="p-4 text-muted-foreground">Discover Page (Coming Soon)</div>} />
        <Route path="search" element={<div className="p-4 text-muted-foreground">Search Page (Coming Soon)</div>} />
        <Route path="library" element={<div className="p-4 text-muted-foreground">Library (Coming Soon)</div>} />
        <Route path="settings" element={<div className="p-4 text-muted-foreground">Settings</div>} />
      </Route>
    </Routes>
  );
}
