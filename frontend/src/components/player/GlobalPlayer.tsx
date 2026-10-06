import { useEffect, useRef } from 'react';
import { usePlayerStore } from '@/stores/usePlayerStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { postInteraction } from '@/api/interactions';
import { Play, Pause, SkipForward, SkipBack, Volume2 } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';

export function GlobalPlayer() {
  const { 
    currentTrack, isPlaying, volume, progress, duration,
    togglePlay, setProgress, setDuration, playNext, playPrevious, setVolume
  } = usePlayerStore();
  
  const userId = useAuthStore(state => state.userId);
  const queryClient = useQueryClient();
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Sync state to audio element
  useEffect(() => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.play().catch(e => console.error("Playback failed:", e));
      } else {
        audioRef.current.pause();
      }
    }
  }, [isPlaying, currentTrack]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  // Handle interaction API logging when a new track plays
  useEffect(() => {
    if (currentTrack && userId) {
      postInteraction({
        user_id: userId,
        song_id: currentTrack.song_id,
        interaction_type: 'PLAY'
      }).catch(console.error);
    }
  }, [currentTrack, userId]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setProgress(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleEnded = () => {
    if (currentTrack && userId) {
      postInteraction({
        user_id: userId,
        song_id: currentTrack.song_id,
        interaction_type: 'COMPLETE'
      }).then(() => {
        queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      }).catch(console.error);
    }
    playNext();
  };

  const handleSkip = () => {
    if (currentTrack && userId) {
      postInteraction({
        user_id: userId,
        song_id: currentTrack.song_id,
        interaction_type: 'SKIP'
      }).then(() => {
        queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      }).catch(console.error);
    }
    playNext();
  };

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = Number(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
      setProgress(newTime);
    }
  };

  const formatTime = (time: number) => {
    if (!time || isNaN(time)) return '0:00';
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!currentTrack) {
    return (
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-card border-t border-border z-50 glass-panel flex items-center justify-center">
        <p className="text-muted-foreground font-medium">Select a track to start listening</p>
      </div>
    );
  }

  // Use the full URL if relative, though VITE_API_BASE_URL is preferred if audio_url doesn't include the domain
  const audioSrc = currentTrack.audio_url.startsWith('http') 
    ? currentTrack.audio_url 
    : `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}${currentTrack.audio_url}`;

  return (
    <div className="absolute bottom-0 left-0 right-0 h-24 bg-card border-t border-border z-50 glass-panel flex items-center justify-between px-4 md:px-8">
      
      {/* Hidden Audio Element */}
      <audio 
        ref={audioRef}
        src={audioSrc}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
      />

      {/* Track Info */}
      <div className="flex items-center gap-4 w-1/4 min-w-[200px]">
        <div className="w-14 h-14 bg-secondary rounded flex-shrink-0 flex items-center justify-center overflow-hidden">
          {currentTrack.cover_url ? (
            <img src={currentTrack.cover_url} alt={currentTrack.title} className="w-full h-full object-cover" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-primary/20" />
          )}
        </div>
        <div className="overflow-hidden">
          <p className="font-bold text-sm truncate text-foreground">{currentTrack.title}</p>
          <p className="text-xs text-muted-foreground truncate">{currentTrack.artist}</p>
        </div>
      </div>

      {/* Player Controls */}
      <div className="flex flex-col items-center justify-center flex-1 max-w-2xl px-4">
        <div className="flex items-center gap-6 mb-2">
          <button onClick={playPrevious} className="text-muted-foreground hover:text-foreground transition">
            <SkipBack size={20} />
          </button>
          
          <button 
            onClick={togglePlay}
            className="w-10 h-10 flex items-center justify-center bg-primary text-primary-foreground rounded-full hover:scale-105 transition"
          >
            {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-1" />}
          </button>
          
          <button onClick={handleSkip} className="text-muted-foreground hover:text-foreground transition">
            <SkipForward size={20} />
          </button>
        </div>
        
        <div className="flex items-center gap-3 w-full">
          <span className="text-xs text-muted-foreground w-10 text-right">{formatTime(progress)}</span>
          <div className="flex-1 group relative flex items-center">
             <input 
               type="range" 
               min="0" 
               max={duration || 100} 
               value={progress} 
               onChange={handleProgressChange}
               className="w-full h-1 bg-secondary rounded-full appearance-none cursor-pointer accent-primary"
             />
          </div>
          <span className="text-xs text-muted-foreground w-10">{formatTime(duration)}</span>
        </div>
      </div>

      {/* Extra Controls */}
      <div className="flex items-center justify-end gap-4 w-1/4 min-w-[150px] hidden md:flex">
        <Volume2 size={20} className="text-muted-foreground" />
        <input 
           type="range" 
           min="0" 
           max="1" 
           step="0.01" 
           value={volume} 
           onChange={(e) => setVolume(Number(e.target.value))}
           className="w-24 h-1 bg-secondary rounded-full appearance-none cursor-pointer accent-primary"
        />
      </div>
    </div>
  );
}
