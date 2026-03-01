import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from '../pages/LoginPage';
import Order from '../pages/OrderPage';
import Dashboard from '../pages/DashboardPage';
import useAuth from '../hooks/useAuth';
import { ROUTES } from '../utils/constants';

const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return isAuthenticated ? children : <Navigate to={ROUTES.LOGIN} />;
};

const AppRoutes = () => {
  return (
    <Router>
      <Routes>
        <Route path={ROUTES.LOGIN} element={<Login />} />
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
