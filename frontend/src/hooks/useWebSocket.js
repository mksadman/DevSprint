import { useEffect, useRef, useState, useCallback } from 'react';
import { WS_URL } from '../utils/constants';

const useWebSocket = (orderId) => {
  const [status, setStatus] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);

  const connect = useCallback(() => {
    if (!orderId) return;

    // Use environment variable or default
    const wsUrl = `${WS_URL}/${orderId}`;
    
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('WebSocket Connected');
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket Message:', data);
        if (data.status) {
          setStatus(data.status);
        }
      } catch (error) {
        console.error('WebSocket message parsing error:', error);
      }
    };

    socket.onclose = () => {
      console.log('WebSocket Disconnected');
      setIsConnected(false);
      // Simple reconnect logic could be added here if needed
      // setTimeout(connect, 3000); 
    };

    socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

  }, [orderId]);

  useEffect(() => {
    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  return { status, isConnected };
};

export default useWebSocket;
