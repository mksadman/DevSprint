import { useState, useEffect, useRef } from 'react';

const useMetricsPolling = (serviceUrl) => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const parseMetrics = (text) => {
    const lines = text.split('\n');
    const parsed = {};
    
    lines.forEach(line => {
      if (!line || line.startsWith('#')) return;
      
      const parts = line.split(' ');
      if (parts.length >= 2) {
        const key = parts[0];
        const value = parseFloat(parts[1]);
        if (!isNaN(value)) {
          parsed[key] = value;
        }
      }
    });
    
    return {
      total_requests: parsed.total_requests || 0,
      total_deductions: parsed.total_deductions || 0,
      failed_deductions: parsed.failed_deductions || 0,
      average_latency_ms: parsed.average_latency_ms || 0
    };
  };

  useEffect(() => {
    const fetchMetrics = async () => {
      if (!serviceUrl) {
        setError('Configuration Error');
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${serviceUrl}/metrics`);
        if (response.ok) {
          const text = await response.text();
          setMetrics(parseMetrics(text));
          setError(null);
        } else {
          setError('Unavailable');
        }
      } catch (err) {
        setError('Unavailable');
      } finally {
        setLoading(false);
      }
    };

    // Initial check
    fetchMetrics();

    // Poll every 5 seconds
    intervalRef.current = setInterval(fetchMetrics, 5000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [serviceUrl]);

  return { metrics, loading, error };
};

export default useMetricsPolling;
