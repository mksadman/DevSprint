import { useState, useEffect, useRef } from 'react';

const useHealthPolling = (serviceUrl) => {
  const [status, setStatus] = useState('UNKNOWN');
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef(null);

  useEffect(() => {
    const checkHealth = async () => {
      if (!serviceUrl) {
        setStatus('CONFIG_ERROR');
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${serviceUrl}/health`);
        if (response.ok) {
          setStatus('UP');
        } else {
          setStatus('DOWN');
        }
      } catch (error) {
        setStatus('DOWN');
      } finally {
        setLoading(false);
      }
    };

    // Initial check
    checkHealth();

    // Poll every 3 seconds
    intervalRef.current = setInterval(checkHealth, 3000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [serviceUrl]);

  return { status, loading };
};

export default useHealthPolling;
