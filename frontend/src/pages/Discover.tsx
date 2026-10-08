import { useState, useEffect } from 'react';
import { getSongs, getSimilarSongs, SuggestedSong, SongItem } from '@/api/songs';
import { usePlayerStore } from '@/stores/usePlayerStore';
import { Play, Loader2, Sparkles, RefreshCw } from 'lucide-react';
import { useAuthStore } from '@/stores/useAuthStore';

export function Discover() {
  const [seedSongs, setSeedSongs] = useState<SongItem[]>([]);
  const [selectedSeed, setSelectedSeed] = useState<SongItem | null>(null);
  const [similarSongs, setSimilarSongs] = useState<SuggestedSong[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDiscovering, setIsDiscovering] = useState(false);
  
  const setTrack = usePlayerStore(state => state.setTrack);
  const userId = useAuthStore(state => state.userId);

  useEffect(() => {
    // Load a few random songs to act as seeds for discovery
    const fetchSeeds = async () => {
      try {
        const res = await getSongs(20, Math.floor(Math.random() * 10));
        setSeedSongs(res.songs.slice(0, 5));
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSeeds();
  }, []);

  const handleDiscover = async (song: SongItem) => {
    setSelectedSeed(song);
    setIsDiscovering(true);
    try {
      const res = await getSimilarSongs(song.song_id, 12, userId || undefined);
      setSimilarSongs(res.suggested_songs);
    } catch (e) {
      console.error(e);
    } finally {
      setIsDiscovering(false);
    }
  };

  return (
    <div className="space-y-12 mt-4">
      <header className="space-y-2">
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">Discover</h1>
        <p className="text-muted-foreground text-lg">Pick a track to explore the acoustic universe around it.</p>
      </header>

      {isLoading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="animate-spin text-primary w-10 h-10" />
        </div>
      ) : (
        <section>
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2"><Sparkles className="text-purple-400"/> Starting Points</h2>
          <div className="flex flex-wrap gap-3">
            {seedSongs.map(song => (
              <button
                key={song.song_id}
                onClick={() => handleDiscover(song)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${selectedSeed?.song_id === song.song_id ? 'bg-primary text-black scale-105' : 'bg-white/10 hover:bg-white/20 text-white'}`}
              >
                {song.title} - {song.artist}
              </button>
            ))}
          </div>
        </section>
      )}

      {isDiscovering ? (
        <div className="flex flex-col items-center justify-center py-24 space-y-4">
           <RefreshCw className="animate-spin text-purple-500 w-12 h-12" />
           <p className="text-lg text-purple-200">Analyzing audio vectors...</p>
        </div>
      ) : similarSongs.length > 0 ? (
        <section className="space-y-6 bg-purple-900/10 p-6 md:p-8 rounded-3xl border border-purple-500/20">
          <div className="space-y-1">
            <h2 className="text-2xl font-bold text-white">Similar to {selectedSeed?.title}</h2>
            <p className="text-purple-300/60 text-sm">Based on deep audio features and acoustic similarity.</p>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {similarSongs.map((song) => (
              <div 
                key={song.song_id} 
                className="flex items-center p-3 rounded-2xl bg-black/40 border border-white/5 hover:bg-white/10 transition-all group cursor-pointer"
                onClick={() => setTrack({
                  id: song.song_id,
                  title: song.title,
                  artist: song.artist,
                  audioUrl: song.audio_url,
                  durationMs: 0
                })}
              >
                <div className="w-14 h-14 rounded-xl bg-purple-500/20 flex items-center justify-center text-purple-400 group-hover:scale-110 group-hover:bg-purple-500 group-hover:text-white transition-all shadow-inner">
                  <Play fill="currentColor" size={20} className="ml-1" />
                </div>
                <div className="ml-4 overflow-hidden pr-2">
                  <h4 className="text-base font-bold text-white truncate">{song.title}</h4>
                  <p className="text-sm text-purple-300/80 truncate">{song.artist}</p>
                  <p className="text-xs font-mono text-purple-400/50 mt-1">Match: {(song.similarity_score * 100).toFixed(1)}%</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
