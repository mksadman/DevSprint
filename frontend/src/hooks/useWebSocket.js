import { useEffect, useRef, useState, useCallback } from 'react';
import { WS_URL } from '../utils/constants';
import useAuth from './useAuth';

const RECONNECT_DELAY_MS = 3000;

const useWebSocket = (orderId) => {
  const { token } = useAuth();
  const [status, setStatus] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  // Track whether the hook is still mounted so we don't reconnect after unmount
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!token) {
      console.warn('WebSocket: no auth token available, skipping connection');
      return;
    }

    // Backend endpoint: /ws?token=<jwt>
    // orderId is NOT part of the URL — the server routes by student_id from the JWT.
    const wsUrl = `${WS_URL}?token=${encodeURIComponent(token)}`;

    console.log(`Connecting to WebSocket: ${WS_URL}?token=<redacted>`);
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
        // The server pushes updates for all of this student's orders.
        // Only surface the status update when it matches the currently viewed order.
        if (data.status && (!orderId || data.order_id === orderId)) {
          setStatus(data.status);
        }
      } catch (error) {
        console.error('WebSocket message parsing error:', error);
      }
    };

    socket.onclose = (event) => {
      console.log('WebSocket Disconnected', event.code, event.reason);
      setIsConnected(false);
      // Auto-reconnect unless the close was intentional (code 1000 / 1008 = auth rejected)
      if (mountedRef.current && event.code !== 1000 && event.code !== 1008) {
        console.log(`Reconnecting in ${RECONNECT_DELAY_MS}ms…`);
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };
  }, [token, orderId]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimerRef.current);
      if (socketRef.current) {
        socketRef.current.close(1000, 'component unmounted');
      }
    };
  }, [connect]);

  return { status, isConnected };
};

export default useWebSocket;
