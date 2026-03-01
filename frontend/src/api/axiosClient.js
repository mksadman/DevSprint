import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

const axiosClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach JWT token
axiosClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor to handle errors (e.g., 401)
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token and redirect to login if needed
      // Note: We avoid direct window.location here to keep it clean, 
      // but in a real app we might trigger an event or use a callback.
      localStorage.removeItem('token');
      // Ideally, the AuthContext should handle the redirect via state change
    }
    return Promise.reject(error);
  }
);

export default axiosClient;
