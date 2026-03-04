import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';
import { ROUTES } from '../../utils/constants';

const Navbar = () => {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate(ROUTES.LOGIN);
    setIsMenuOpen(false);
  };

  const isActive = (path) => location.pathname === path;

  const getLinkClass = (path) => 
    `px-3 py-2 rounded-md text-sm font-medium transition-colors block ${
      isActive(path) ? 'bg-emerald-700 text-white' : 'text-emerald-100 hover:bg-emerald-500'
    }`;

  return (
    <nav className="bg-emerald-600 text-white shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <Link to={ROUTES.ORDER} className="text-xl font-bold tracking-tight flex items-center gap-2 mr-8">
              Cafeteria Crisis
            </Link>
            <div className="hidden md:flex space-x-4">
              <Link to={ROUTES.ORDER} className={getLinkClass(ROUTES.ORDER)}>
                Place Order
              </Link>
              <Link to={ROUTES.DASHBOARD} className={getLinkClass(ROUTES.DASHBOARD)}>
                Track Order
              </Link>
              <Link to={ROUTES.ADMIN} className={getLinkClass(ROUTES.ADMIN)}>
                Admin
              </Link>
            </div>
          </div>
          
          {/* Desktop User Menu */}
          <div className="hidden md:flex items-center space-x-4">
            {user && (
              <span className="text-sm text-emerald-100">
                Hi, {user.studentId || 'Student'}
              </span>
            )}
            <button
              onClick={handleLogout}
              className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-emerald-600 bg-white hover:bg-emerald-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-emerald-600 focus:ring-white transition-colors"
            >
              Logout
            </button>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-emerald-100 hover:text-white focus:outline-none p-2"
              aria-label="Toggle menu"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {isMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Menu Dropdown */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-emerald-500 animate-fadeIn">
            <div className="flex flex-col space-y-2">
              <Link 
                to={ROUTES.ORDER} 
                className={getLinkClass(ROUTES.ORDER)}
                onClick={() => setIsMenuOpen(false)}
              >
                Place Order
              </Link>
              <Link 
                to={ROUTES.DASHBOARD} 
                className={getLinkClass(ROUTES.DASHBOARD)}
                onClick={() => setIsMenuOpen(false)}
              >
                Track Order
              </Link>
              <Link 
                to={ROUTES.ADMIN} 
                className={getLinkClass(ROUTES.ADMIN)}
                onClick={() => setIsMenuOpen(false)}
              >
                Admin
              </Link>
              
              <div className="pt-4 border-t border-emerald-500 mt-2 space-y-3">
                {user && (
                  <div className="px-3 text-sm text-emerald-100 font-medium">
                    Hi, {user.studentId || 'Student'}
                  </div>
                )}
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-sm font-medium text-emerald-100 hover:bg-emerald-500 rounded-md transition-colors"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
