import React from 'react';
import HealthGrid from '../components/admin/HealthGrid';
import MetricsPanel from '../components/admin/MetricsPanel';
import ChaosControls from '../components/admin/ChaosControls';

const AdminPage = () => {
  const services = [
    { 
      id: 'auth', 
      name: 'Auth Service', 
      url: import.meta.env.VITE_AUTH_URL 
    },
    { 
      id: 'gateway', 
      name: 'Order Gateway', 
      url: import.meta.env.VITE_GATEWAY_URL 
    },
    { 
      id: 'stock', 
      name: 'Stock Service', 
      url: import.meta.env.VITE_STOCK_URL 
    },
    { 
      id: 'kitchen', 
      name: 'Kitchen Service', 
      url: import.meta.env.VITE_KITCHEN_URL 
    },
    { 
      id: 'notification', 
      name: 'Notification Service', 
      url: import.meta.env.VITE_NOTIFICATION_URL 
    },
  ];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8 border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-800">Admin Monitoring Dashboard</h1>
        <p className="text-gray-500 mt-1">Real-time system status and chaos engineering controls</p>
      </div>

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-700 mb-4 uppercase tracking-wide text-xs">System Health</h2>
        <HealthGrid services={services} />
      </section>

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-700 mb-4 uppercase tracking-wide text-xs">Live Metrics</h2>
        <MetricsPanel services={services} />
      </section>

      <section className="mb-10">
        <ChaosControls services={services} />
      </section>
    </div>
  );
};

export default AdminPage;
