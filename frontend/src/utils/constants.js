export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8004/ws';

export const ORDER_STATUS = {
  PENDING: 'PENDING',
  STOCK_VERIFIED: 'STOCK_VERIFIED',
  IN_KITCHEN: 'IN_KITCHEN',
  READY: 'READY',
  CANCELLED: 'CANCELLED',
};

export const ROUTES = {
  LOGIN: '/login',
  ORDER: '/order',
  DASHBOARD: '/dashboard',
};
