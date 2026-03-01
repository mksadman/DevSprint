import React from 'react';
import ServiceCard from './ServiceCard';

const HealthGrid = ({ services }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
      {services.map((service) => (
        <ServiceCard 
          key={service.id} 
          name={service.name} 
          url={service.url} 
        />
      ))}
    </div>
  );
};

export default HealthGrid;
