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
    <div className="space-y-8">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Good evening, {userId}</h1>
      </header>

      {isLoading ? (
        <section>
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-2xl font-bold">Made for you</h2>
            <Loader2 className="animate-spin text-primary" size={24} />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="bg-card p-4 rounded-xl border border-border space-y-4">
                <div className="aspect-square bg-secondary rounded-md animate-pulse"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-secondary rounded w-3/4 animate-pulse"></div>
                  <div className="h-3 bg-secondary rounded w-1/2 animate-pulse"></div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : isError ? (
        <section className="bg-destructive/10 p-6 rounded-xl border border-destructive/20 text-center space-y-4">
           <h2 className="text-xl font-bold text-destructive">Could not load recommendations</h2>
           <p className="text-muted-foreground">{error instanceof Error ? error.message : 'Unknown error occurred'}</p>
        </section>
      ) : recommendations && recommendations.length > 0 ? (
        <section>
          <h2 className="text-2xl font-bold mb-4">Made for you</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {recommendations.map((rec) => (
              <RecommendationCard key={rec.id} recommendation={rec} />
            ))}
          </div>
        </section>
      ) : (
        <section className="text-center py-20 space-y-4 border border-dashed border-border rounded-xl">
           <h2 className="text-xl font-bold text-muted-foreground">Your catalog is warming up</h2>
           <p className="text-muted-foreground">We are preparing your personalized recommendations. Try interacting with some songs first!</p>
        </section>
      )}
    </div>
  );
}
