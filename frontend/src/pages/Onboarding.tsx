import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Onboarding() {
  const navigate = useNavigate();
  useEffect(() => {
    // Backwards-compat route: onboarding now lives under Goals.
    navigate('/goals', { replace: true });
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-gray-50 flex items-center justify-center">
      <div className="text-sm text-gray-500">Redirecting…</div>
    </div>
  );
}
