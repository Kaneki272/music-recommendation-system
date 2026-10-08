import { useState, useEffect } from 'react';
import { getSongs, SongItem } from '@/api/songs';
import { usePlayerStore } from '@/stores/usePlayerStore';
import { Play, Search as SearchIcon, Loader2 } from 'lucide-react';

export function Search() {
  const [query, setQuery] = useState('');
  const [songs, setSongs] = useState<SongItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const setTrack = usePlayerStore(state => state.setTrack);

  useEffect(() => {
    const fetchCatalog = async () => {
      try {
        setIsLoading(true);
        // In a real app with large catalogs, we'd pass query to backend. 
        // Here we fetch a large batch and filter locally for responsiveness.
        const res = await getSongs(200, 0);
        setSongs(res.songs);
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCatalog();
  }, []);

  const filteredSongs = songs.filter(song => 
    song.title.toLowerCase().includes(query.toLowerCase()) || 
    song.artist.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-8 mt-4">
      <header className="space-y-4">
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">Search</h1>
        <div className="relative max-w-xl">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <SearchIcon className="h-5 w-5 text-muted-foreground" />
          </div>
          <input
            type="text"
            className="block w-full pl-12 pr-4 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent transition-all outline-none"
            placeholder="What do you want to listen to?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </header>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="animate-spin text-primary w-10 h-10" />
        </div>
      ) : filteredSongs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSongs.map((song) => (
            <div 
              key={song.song_id} 
              className="flex items-center p-3 rounded-xl bg-white/5 border border-transparent hover:bg-white/10 hover:border-white/20 transition-all group cursor-pointer"
              onClick={() => setTrack({
                id: song.song_id,
                title: song.title,
                artist: song.artist,
                audioUrl: song.audio_url,
                durationMs: 0
              })}
            >
              <div className="w-12 h-12 rounded-lg bg-black/40 flex items-center justify-center text-primary group-hover:scale-105 transition-transform">
                <Play fill="currentColor" size={20} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                <span className="opacity-100 group-hover:opacity-0 absolute font-bold">♪</span>
              </div>
              <div className="ml-4 overflow-hidden">
                <h4 className="text-base font-semibold text-white truncate">{song.title}</h4>
                <p className="text-sm text-muted-foreground truncate">{song.artist}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <p className="text-lg text-muted-foreground">No results found for "{query}"</p>
        </div>
      )}
    </div>
  );
}
