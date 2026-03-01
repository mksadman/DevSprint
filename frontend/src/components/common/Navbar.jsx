import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';
import { ROUTES } from '../../utils/constants';

const Navbar = () => {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate(ROUTES.LOGIN);
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="bg-blue-600 text-white shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-8">
            <Link to={ROUTES.ORDER} className="text-xl font-bold tracking-tight">
              Cafeteria Crisis
            </Link>
            <div className="hidden md:flex space-x-4">
              <Link
                to={ROUTES.ORDER}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive(ROUTES.ORDER) ? 'bg-blue-700 text-white' : 'text-blue-100 hover:bg-blue-500'
                }`}
              >
                Place Order
              </Link>
              <Link
                to={ROUTES.DASHBOARD}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive(ROUTES.DASHBOARD) ? 'bg-blue-700 text-white' : 'text-blue-100 hover:bg-blue-500'
                }`}
              >
                Track Order
              </Link>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {user && (
              <span className="text-sm text-blue-100 hidden sm:block">
                Hi, {user.studentId || 'Student'}
              </span>
            )}
            <button
              onClick={handleLogout}
              className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-600 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-blue-600 focus:ring-white"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
