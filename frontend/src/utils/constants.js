export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api';
export const AUTH_API_BASE_URL = import.meta.env.VITE_AUTH_API_BASE_URL || 'http://localhost:3000/api/auth';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:3000/ws';

export const ORDER_STATUS = {
  PENDING: 'PENDING',
  STOCK_VERIFIED: 'STOCK_VERIFIED',
  IN_KITCHEN: 'IN_KITCHEN',
  READY: 'READY',
  CANCELLED: 'CANCELLED',
};

export const ROUTES = {
  LOGIN: '/login',
  REGISTER: '/register',
  ORDER: '/order',
  DASHBOARD: '/dashboard',
  ADMIN: '/admin',
};

export const MENU_ITEMS = [
  { id: '550e8400-e29b-41d4-a716-446655440001', name: 'Burger', price: 5.99, description: 'Juicy beef patty with fresh lettuce and tomato' },
  { id: '550e8400-e29b-41d4-a716-446655440002', name: 'Pizza', price: 8.99, description: 'Classic cheese pizza with tomato sauce' },
  { id: '550e8400-e29b-41d4-a716-446655440003', name: 'Salad', price: 4.99, description: 'Fresh garden salad with vinaigrette' },
  { id: '550e8400-e29b-41d4-a716-446655440004', name: 'Fries', price: 2.99, description: 'Crispy golden french fries' },
  { id: '550e8400-e29b-41d4-a716-446655440005', name: 'Soda', price: 1.99, description: 'Refreshing carbonated beverage' },
];
