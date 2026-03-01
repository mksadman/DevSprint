import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { register } from '../api/authApi';
import useAuth from '../hooks/useAuth';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import { ROUTES } from '../utils/constants';

const RegisterPage = () => {
  const [studentId, setStudentId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // 1. Register the user
      await register(studentId, password);
      
      // 2. Auto-login the user
      await login(studentId, password);
      
      // 3. Redirect to Order page
      navigate(ROUTES.ORDER);
    } catch (err) {
      if (err.response && err.response.status === 409) {
        setError('Student ID already exists.');
      } else if (err.response && err.response.status === 422) {
        setError('Validation error. Password must be at least 6 characters.');
      } else {
        setError('Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow-lg w-full max-w-md border border-emerald-100">
        <div className="text-center mb-8">
           <h2 className="text-3xl font-bold text-gray-800">Join Us</h2>
           <p className="text-gray-500 mt-2">Create your account to get started</p>
         </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="Student ID"
            name="studentId"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            required
            placeholder="Enter your Student ID"
            className="focus:ring-emerald-500 focus:border-emerald-500"
          />
          <Input
            label="Password"
            name="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="Choose a password (min 6 chars)"
            className="focus:ring-emerald-500 focus:border-emerald-500"
          />
          <div className="flex flex-col gap-4 mt-8">
            <Button 
              type="submit" 
              loading={loading} 
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-lg transition-all shadow-md hover:shadow-lg"
            >
              Create Account
            </Button>
            <div className="text-center mt-4">
              <span className="text-gray-500">Already have an account? </span>
              <button
                type="button"
                onClick={() => navigate(ROUTES.LOGIN)}
                className="text-emerald-600 hover:text-emerald-800 font-semibold focus:outline-none hover:underline"
              >
                Sign in here
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RegisterPage;
