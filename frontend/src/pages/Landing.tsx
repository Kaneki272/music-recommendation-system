import { useNavigate } from 'react-router-dom';

export function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[128px] -z-10" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[128px] -z-10" />

      <div className="max-w-3xl text-center space-y-8">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight">
          Music that learns what you <span className="text-primary">actually</span> like.
        </h1>
        
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Experience a hybrid recommendation engine that combines collaborative filtering and acoustic similarity to find your next favorite track.
        </p>

        <div className="flex items-center justify-center gap-4 pt-8">
          <button 
            onClick={() => navigate('/auth')}
            className="bg-primary text-primary-foreground px-8 py-4 rounded-full font-bold text-lg hover:scale-105 transition-transform"
          >
            Start Listening
          </button>
        </div>
      </div>
    </div>
  );
}
