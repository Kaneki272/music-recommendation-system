import { useState } from 'react';
import { Play, Heart, SkipForward } from 'lucide-react';
import type { TrackResponse } from '@/api/recommendations';
import { usePlayerStore } from '@/stores/usePlayerStore';
import { postInteraction } from '@/api/interactions';
import { useAuthStore } from '@/stores/useAuthStore';
import { useQueryClient } from '@tanstack/react-query';

interface RecommendationCardProps {
  recommendation: TrackResponse;
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const { play } = usePlayerStore();
  const userId = useAuthStore(state => state.userId);
  const queryClient = useQueryClient();

  const handlePlay = () => {
    // Determine the audio URL
    const audio_url = recommendation.audio_url || `/api/v1/songs/${recommendation.id}/stream`;
    
    play({
      song_id: recommendation.id,
      title: recommendation.title,
      artist: recommendation.artist?.name || 'Unknown Artist',
      audio_url: audio_url,
      cover_url: recommendation.album?.cover_image_url
    });
  };

  const [isLiked, setIsLiked] = useState(false);
  const [isSkipped, setIsSkipped] = useState(false);

  const handleLike = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (userId && !isLiked) {
      setIsLiked(true);
      postInteraction({
        user_id: userId,
        song_id: recommendation.id,
        interaction_type: 'LIKE',
        weight: 1.0
      }).then(() => {
        queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      }).catch(console.error);
    }
  };

  const handleSkip = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (userId && !isSkipped) {
      setIsSkipped(true);
      postInteraction({
        user_id: userId,
        song_id: recommendation.id,
        interaction_type: 'SKIP',
        weight: 1.0
      }).then(() => {
        queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      }).catch(console.error);
    }
  };

  const scoreDisplay = recommendation.match_score 
    ? `${(recommendation.match_score * 100).toFixed(1)}%` 
    : '';

  return (
    <div 
      onClick={handlePlay}
      className={`group relative bg-card/40 hover:bg-card/80 p-4 rounded-2xl border border-white/5 hover:border-white/20 transition-all duration-300 cursor-pointer flex flex-col gap-4 shadow-lg hover:shadow-2xl hover:-translate-y-1 ${isSkipped ? 'opacity-40 grayscale' : ''}`}
    >
      <div className="relative aspect-square bg-white/5 rounded-xl overflow-hidden shadow-inner">
        {recommendation.album?.cover_image_url ? (
          <img 
            src={recommendation.album.cover_image_url} 
            alt={recommendation.title} 
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/20 via-black to-purple-500/20 text-muted-foreground group-hover:scale-110 transition-transform duration-500">
            <span className="text-5xl opacity-50">♪</span>
          </div>
        )}
        
        {/* Glassmorphism overlay for interactions */}
        <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 transition-all duration-300 flex items-center justify-center gap-3 rounded-xl">
           <button 
             onClick={handleLike}
             className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 ${isLiked ? 'bg-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.5)] text-white scale-110' : 'bg-white/10 text-white hover:bg-rose-500 hover:scale-110'}`}
             title={isLiked ? "Liked" : "Like"}
           >
             <Heart size={20} fill={isLiked ? "currentColor" : "none"} className={isLiked ? "animate-pulse" : ""} />
           </button>
           <button 
             className="w-16 h-16 rounded-full bg-primary text-black flex items-center justify-center hover:scale-110 transition-all duration-300 shadow-[0_0_20px_rgba(29,185,84,0.4)]"
             title="Play"
           >
             <Play size={28} fill="currentColor" className="ml-1" />
           </button>
           <button 
             onClick={handleSkip}
             className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 ${isSkipped ? 'bg-white text-black' : 'bg-white/10 text-white hover:bg-white hover:text-black hover:scale-110'}`}
             title={isSkipped ? "Skipped" : "Skip"}
           >
             <SkipForward size={20} />
           </button>
        </div>
      </div>
      
      <div className="space-y-1.5 px-1">
        <h3 className="font-extrabold text-foreground truncate text-lg tracking-tight group-hover:text-primary transition-colors">{recommendation.title}</h3>
        <p className="text-sm text-muted-foreground truncate font-medium">{recommendation.artist?.name || 'Unknown Artist'}</p>
        
        {scoreDisplay && (
          <div className="pt-2 flex justify-between items-center text-xs">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-primary bg-primary/10 font-medium">
              {recommendation.recommendation_reason}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
