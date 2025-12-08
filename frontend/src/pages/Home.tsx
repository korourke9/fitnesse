import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function Home() {
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to onboarding immediately
    navigate('/onboarding', { replace: true });
  }, [navigate]);

  return null;
}

export default Home;

