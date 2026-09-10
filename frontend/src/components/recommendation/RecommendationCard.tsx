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
      className={`group bg-card hover:bg-secondary/50 p-4 rounded-xl border border-transparent hover:border-border transition-all cursor-pointer flex flex-col gap-4 relative ${isSkipped ? 'opacity-50 grayscale' : ''}`}
    >
      <div className="relative aspect-square bg-secondary rounded-lg overflow-hidden shadow-md">
        {recommendation.album?.cover_image_url ? (
          <img 
            src={recommendation.album.cover_image_url} 
            alt={recommendation.title} 
            className="w-full h-full object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/20 to-purple-500/20 text-muted-foreground group-hover:scale-105 transition-transform">
            <span className="text-4xl">♪</span>
          </div>
        )}
        
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4">
           <button 
             onClick={handleLike}
             className={`w-10 h-10 rounded-full flex items-center justify-center transition ${isLiked ? 'bg-red-500/80 text-white' : 'bg-black/60 text-white hover:bg-primary hover:text-black'}`}
             title={isLiked ? "Liked" : "Like"}
           >
             <Heart size={18} fill={isLiked ? "currentColor" : "none"} />
           </button>
           <button 
             className="w-14 h-14 rounded-full bg-primary text-black flex items-center justify-center hover:scale-105 transition shadow-lg"
             title="Play"
           >
             <Play size={24} fill="currentColor" className="ml-1" />
           </button>
           <button 
             onClick={handleSkip}
             className={`w-10 h-10 rounded-full flex items-center justify-center transition ${isSkipped ? 'bg-white text-black' : 'bg-black/60 text-white hover:bg-white hover:text-black'}`}
             title={isSkipped ? "Skipped" : "Skip"}
           >
             <SkipForward size={18} />
           </button>
        </div>
      </div>
      
      <div className="space-y-1">
        <h3 className="font-bold text-foreground truncate">{recommendation.title}</h3>
        <p className="text-sm text-muted-foreground truncate">{recommendation.artist?.name || 'Unknown Artist'}</p>
        <div className="flex justify-between items-center text-xs text-muted-foreground/60">
          {scoreDisplay && <span>Match: {scoreDisplay}</span>}
          {recommendation.recommendation_reason && <span className="truncate max-w-[100px]">{recommendation.recommendation_reason}</span>}
        </div>
      </div>
    </div>
  );
}
