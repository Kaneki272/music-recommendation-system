import { Outlet } from 'react-router-dom';
import { Home, Compass, Search, Library, Settings, LogOut } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { GlobalPlayer } from '@/components/player/GlobalPlayer';
import { useAuthStore } from '@/stores/useAuthStore';

export function Shell() {
  const logout = useAuthStore(state => state.logout);
  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-card border-r border-border hidden md:flex flex-col">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <span className="text-3xl tracking-tighter">M</span>
            Music Rec
          </h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-2">
          <NavItem to="/home" icon={<Home size={20} />} label="Home" />

        </nav>
        
        <div className="p-4 border-t border-border">
          <NavItem to="/settings" icon={<Settings size={20} />} label="Settings" />
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative overflow-hidden">
        
        {/* Top Right Actions */}
        <div className="absolute top-4 right-4 md:top-8 md:right-8 z-10 hidden md:block">
          <button 
            onClick={() => logout()}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/50 hover:bg-secondary text-foreground transition text-sm font-medium backdrop-blur-sm"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>

        {/* Mobile Header */}
        <header className="md:hidden flex items-center justify-between p-4 bg-card border-b border-border z-10">
           <h1 className="text-xl font-bold text-primary">Music Rec</h1>
           <button 
            onClick={() => logout()}
            className="p-2 rounded-full bg-secondary text-foreground hover:bg-secondary/80 transition"
          >
            <LogOut size={16} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4 pb-28 md:p-8 md:pb-32">
          <Outlet />
        </div>
      </main>

      {/* Global Bottom Player */}
      <GlobalPlayer />
    </div>
  );
}

function NavItem({ to, icon, label }: { to: string, icon: React.ReactNode, label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => cn(
        "flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium",
        isActive 
          ? "bg-secondary text-primary" 
          : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
      )}
    >
      {icon}
      {label}
    </NavLink>
  );
}
