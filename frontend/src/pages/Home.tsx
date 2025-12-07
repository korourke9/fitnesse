import { useEffect, useState } from 'react';
import { apiClient } from '../lib/api';

function Home() {
  const [healthStatus, setHealthStatus] = useState<string>('Checking...');

  useEffect(() => {
    apiClient
      .get('/health')
      .then((response) => {
        setHealthStatus(response.data.status);
      })
      .catch((error) => {
        setHealthStatus('Error connecting to API');
        console.error('API error:', error);
      });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Fitnesse</h1>
        <p className="text-lg text-gray-600 mb-8">
          AI-driven personalized fitness and nutrition
        </p>
        <div className="bg-white p-6 rounded-lg shadow-md">
          <p className="text-sm text-gray-500">API Status:</p>
          <p className="text-lg font-semibold text-green-600">{healthStatus}</p>
        </div>
      </div>
    </div>
  );
}

export default Home;

