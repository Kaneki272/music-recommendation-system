import { create } from 'zustand';

export interface Track {
  song_id: string;
  title: string;
  artist: string;
  audio_url: string;
  cover_url?: string;
}

interface PlayerState {
  currentTrack: Track | null;
  queue: Track[];
  isPlaying: boolean;
  volume: number;
  progress: number;
  duration: number;
  
  play: (track?: Track) => void;
  pause: () => void;
  togglePlay: () => void;
  setVolume: (volume: number) => void;
  setProgress: (progress: number) => void;
  setDuration: (duration: number) => void;
  
  addToQueue: (track: Track) => void;
  playNext: () => void;
  playPrevious: () => void;
}

export const usePlayerStore = create<PlayerState>((set, get) => ({
  currentTrack: null,
  queue: [],
  isPlaying: false,
  volume: 1, // 0 to 1
  progress: 0,
  duration: 0,

  play: (track) => {
    if (track) {
      set({ currentTrack: track, isPlaying: true });
    } else {
      set({ isPlaying: true });
    }
  },
  
  pause: () => set({ isPlaying: false }),
  
  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
  
  setVolume: (volume) => set({ volume }),
  
  setProgress: (progress) => set({ progress }),
  
  setDuration: (duration) => set({ duration }),
  
  addToQueue: (track) => set((state) => ({ queue: [...state.queue, track] })),
  
  playNext: () => {
    // Simple mock queue behavior for now
    const { queue } = get();
    if (queue.length > 0) {
      const nextTrack = queue[0];
      set({ currentTrack: nextTrack, queue: queue.slice(1), isPlaying: true });
    } else {
      set({ currentTrack: null, isPlaying: false, progress: 0 });
    }
  },
  
  playPrevious: () => {
    // Mock play previous: just restart the track
    set({ progress: 0, isPlaying: true });
  }
}));
