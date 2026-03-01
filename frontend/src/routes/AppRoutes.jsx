import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from '../pages/LoginPage';
import Register from '../pages/RegisterPage';
import Order from '../pages/OrderPage';
import Dashboard from '../pages/DashboardPage';
import useAuth from '../hooks/useAuth';
import MainLayout from '../components/layout/MainLayout';
import { ROUTES } from '../utils/constants';

const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return isAuthenticated ? (
    <MainLayout>
      {children}
    </MainLayout>
  ) : (
    <Navigate to={ROUTES.LOGIN} />
  );
};

const AppRoutes = () => {
  return (
    <Router>
      <Routes>
        <Route path={ROUTES.LOGIN} element={<Login />} />
        <Route path={ROUTES.REGISTER} element={<Register />} />
        <Route 
          path={ROUTES.ORDER} 
          element={
            <PrivateRoute>
              <Order />
            </PrivateRoute>
          } 
        />
        <Route 
          path={ROUTES.DASHBOARD} 
          element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          } 
        />
        <Route path="*" element={<Navigate to={ROUTES.LOGIN} />} />
      </Routes>
    </Router>
  );
};

export default AppRoutes;
