import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppState } from '../lib/state';

function Home() {
  const navigate = useNavigate();
  const { data, isLoading } = useAppState();

  useEffect(() => {
    if (isLoading) return;
    const onboardingComplete = data?.onboarding_complete ?? false;
    navigate(onboardingComplete ? '/dashboard' : '/goals', { replace: true });
  }, [navigate, data, isLoading]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="text-sm text-gray-500">Loading Fitnesse…</div>
      </div>
    </div>
  );
}

export default Home;

