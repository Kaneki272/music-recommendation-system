import { useQuery } from '@tanstack/react-query';
import { getRecommendations } from '@/api/recommendations';
import { useAuthStore } from '@/stores/useAuthStore';
import { RecommendationCard } from '@/components/recommendation/RecommendationCard';
import { Loader2 } from 'lucide-react';

export function Home() {
  const userId = useAuthStore(state => state.userId);

  const { data: recommendations, isLoading, isError, error } = useQuery({
    queryKey: ['recommendations', userId],
    queryFn: () => getRecommendations(userId || 'default', 15),
    enabled: !!userId,
  });

  return (
    <div className="space-y-12">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 mt-8 mb-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-500">Good evening</h1>
          <p className="text-muted-foreground mt-2 text-lg">Here's what we've queued up for you, {userId}</p>
        </div>
      </header>

      {isLoading ? (
        <section>
          <div className="flex items-center gap-3 mb-6">
            <h2 className="text-2xl font-bold tracking-tight">Curating your mix...</h2>
            <Loader2 className="animate-spin text-primary" size={24} />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="bg-card p-4 rounded-2xl border border-white/5 space-y-4 shadow-xl">
                <div className="aspect-square bg-white/5 rounded-xl animate-pulse"></div>
                <div className="space-y-3">
                  <div className="h-4 bg-white/10 rounded w-3/4 animate-pulse"></div>
                  <div className="h-3 bg-white/5 rounded w-1/2 animate-pulse"></div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : isError ? (
        <section className="bg-red-500/10 p-8 rounded-2xl border border-red-500/20 text-center space-y-4 max-w-2xl mx-auto mt-12">
           <h2 className="text-2xl font-bold text-red-400">Could not load recommendations</h2>
           <p className="text-red-300/80">{error instanceof Error ? error.message : 'Unknown error occurred'}</p>
        </section>
      ) : recommendations && recommendations.length > 0 ? (
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl md:text-3xl font-bold tracking-tight">Recommended for You</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 md:gap-6">
            {recommendations.map((rec) => (
              <RecommendationCard key={rec.id} recommendation={rec} />
            ))}
          </div>
        </section>
      ) : (
        <section className="text-center py-24 space-y-6 border border-dashed border-white/10 rounded-3xl bg-white/5 backdrop-blur-sm max-w-3xl mx-auto mt-12">
           <div className="mx-auto w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
             <span className="text-3xl text-primary">♪</span>
           </div>
           <h2 className="text-2xl font-bold text-white">Your catalog is warming up</h2>
           <p className="text-muted-foreground max-w-md mx-auto text-lg">We are preparing your personalized recommendations. Try interacting with some songs to help us learn your taste!</p>
        </section>
      )}
    </div>
  );
}
