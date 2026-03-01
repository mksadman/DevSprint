import React, { useState } from 'react';

const ChaosButton = ({ name, url }) => {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null); // 'success' | 'error'

  const handleKill = async () => {
    if (!url) return;
    
    setLoading(true);
    setStatus(null);
    
    try {
      const response = await fetch(`${url}/chaos/kill`, {
        method: 'POST',
      });
      
      if (response.ok) {
        setStatus('success');
        setTimeout(() => setStatus(null), 3000);
      } else {
        setStatus('error');
        setTimeout(() => setStatus(null), 3000);
      }
    } catch (error) {
      setStatus('error');
      setTimeout(() => setStatus(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col">
      <button
        onClick={handleKill}
        disabled={loading}
        className={`
          w-full px-4 py-3 rounded-lg font-medium text-white transition-colors
          ${loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-red-600 hover:bg-red-700 active:bg-red-800'}
        `}
      >
        {loading ? 'Killing...' : `Kill ${name}`}
      </button>
      {status === 'error' && (
        <span className="text-xs text-red-500 mt-1 text-center">Failed to send command</span>
      )}
      {status === 'success' && (
        <span className="text-xs text-green-500 mt-1 text-center">Command sent</span>
      )}
    </div>
  );
};

const ChaosControls = ({ services }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 border-t-4 border-t-red-500">
      <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
        <span className="mr-2">⚠️</span> Chaos Engineering Controls
      </h2>
      <p className="text-gray-500 text-sm mb-6">
        Danger Zone: These controls will simulate service failures by shutting down the respective microservices.
        The system should automatically detect the failure and reflect it in the Health Grid.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {services.map((service) => (
          <ChaosButton 
            key={service.id} 
            name={service.name} 
            url={service.url} 
          />
        ))}
      </div>
    </div>
  );
};

export default ChaosControls;
