import React from 'react';
import useHealthPolling from '../../hooks/useHealthPolling';

const ServiceCard = ({ name, url }) => {
  const { status, loading } = useHealthPolling(url);

  const isUp = status === 'UP';
  const isDown = status === 'DOWN' || status === 'CONFIG_ERROR';
  
  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 flex flex-col items-center justify-center space-y-2">
      <h3 className="font-medium text-gray-700">{name}</h3>
      
      <div className="flex items-center space-x-2">
        <div 
          className={`w-3 h-3 rounded-full ${
            loading ? 'bg-gray-400 animate-pulse' : 
            isUp ? 'bg-green-500' : 'bg-red-500'
          }`}
        />
        <span className={`text-sm font-bold ${
          loading ? 'text-gray-500' : 
          isUp ? 'text-green-600' : 'text-red-600'
        }`}>
          {loading ? 'CHECKING' : status}
        </span>
      </div>
    </div>
  );
};

export default ServiceCard;
