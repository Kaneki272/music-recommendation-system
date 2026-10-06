import { create } from 'zustand';

interface AuthState {
  userId: string | null;
  isAuthenticated: boolean;
  login: (userId: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  userId: localStorage.getItem('music_user_id') || null,
  isAuthenticated: !!localStorage.getItem('music_user_id'),
  login: (userId) => {
    localStorage.setItem('music_user_id', userId);
    set({ userId, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('music_user_id');
    set({ userId: null, isAuthenticated: false });
  },
}));
