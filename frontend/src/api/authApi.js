import axios from 'axios';
import { AUTH_API_BASE_URL } from '../utils/constants';

// Create a separate client for Auth Service (Port 8001)
const authClient = axios.create({
  baseURL: AUTH_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const login = async (studentId, password) => {
  // Backend auth service (port 8001) serves at /login
  const response = await authClient.post('/login', { student_id: studentId, password });
  return response.data;
};

export const register = async (studentId, password) => {
  // Backend auth service (port 8001) serves at /register
  const response = await authClient.post('/register', { student_id: studentId, password });
  return response.data;
};
