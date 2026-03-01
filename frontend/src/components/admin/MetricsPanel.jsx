import React from 'react';
import useMetricsPolling from '../../hooks/useMetricsPolling';

const MetricItem = ({ label, value }) => (
  <div className="flex justify-between items-center text-sm py-1 border-b border-gray-100 last:border-0">
    <span className="text-gray-500">{label}</span>
    <span className="font-mono font-medium text-gray-700">{value}</span>
  </div>
);

const ServiceMetricCard = ({ name, url }) => {
  const { metrics, loading, error } = useMetricsPolling(url);

  if (loading) {
    return (
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 h-full flex items-center justify-center">
        <div className="text-gray-400 text-sm animate-pulse">Loading metrics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 h-full flex flex-col items-center justify-center text-red-500">
        <span className="text-xs font-medium uppercase tracking-wider mb-1">{name}</span>
        <span className="text-sm">Metrics Unavailable</span>
      </div>
    );
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 h-full">
      <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 border-b border-gray-100 pb-2">
        {name} Metrics
      </h4>
      <div className="space-y-1">
        <MetricItem label="Total Requests" value={metrics?.total_requests ?? '-'} />
        <MetricItem label="Avg Latency" value={`${metrics?.average_latency_ms?.toFixed(2) ?? '-'} ms`} />
        {(metrics?.total_deductions !== undefined) && (
           <MetricItem label="Total Deductions" value={metrics.total_deductions} />
        )}
        {(metrics?.failed_deductions !== undefined) && (
           <MetricItem label="Failed Deductions" value={metrics.failed_deductions} />
        )}
      </div>
    </div>
  );
};

const MetricsPanel = ({ services }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-8">
      {services.map((service) => (
        <ServiceMetricCard 
          key={service.id} 
          name={service.name} 
          url={service.url} 
        />
      ))}
    </div>
  );
};

export default MetricsPanel;
