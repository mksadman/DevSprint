import React from 'react';
import useMetricsPolling from '../../hooks/useMetricsPolling';

const MetricItem = ({ label, value }) => (
  <div className="flex justify-between items-center text-sm py-1 border-b border-gray-100 last:border-0">
    <span className="text-gray-500">{label}</span>
    <span className="font-mono font-medium text-gray-700">{value}</span>
  </div>
);

/**
 * Polls the Order Gateway /metrics endpoint and renders a red alert banner
 * when the 30-second rolling average exceeds 1 000 ms.
 */
const GatewayAlertBanner = ({ gatewayUrl }) => {
  const { metrics } = useMetricsPolling(gatewayUrl);
  if (!metrics?.latency_alert) return null;

  return (
    <div className="mb-6 flex items-start gap-3 rounded-lg border border-red-400 bg-red-50 px-4 py-3 text-red-700 shadow-sm">
      <span className="mt-0.5 text-lg" aria-hidden>⚠️</span>
      <div>
        <p className="font-bold text-sm">Gateway Latency Alert</p>
        <p className="text-xs mt-0.5">
          30-second rolling average is{' '}
          <span className="font-mono font-semibold">
            {metrics.rolling_window_avg_ms?.toFixed(0)} ms
          </span>
          {' '}— exceeds the 1 000 ms threshold.
          Response times are degraded; consider scaling or investigating downstream services.
        </p>
      </div>
    </div>
  );
};

const ServiceMetricCard = ({ name, url }) => {
  const { metrics, loading, error } = useMetricsPolling(url);

  const isAlerting = metrics?.latency_alert === true;

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
    <div
      className={`bg-white p-4 rounded-lg shadow-sm border h-full transition-colors ${
        isAlerting ? 'border-red-400 ring-1 ring-red-300' : 'border-gray-200'
      }`}
    >
      <h4
        className={`text-xs font-bold uppercase tracking-wider mb-3 border-b pb-2 ${
          isAlerting ? 'text-red-500 border-red-100' : 'text-gray-400 border-gray-100'
        }`}
      >
        {name} Metrics
        {isAlerting && <span className="ml-1">⚠️</span>}
      </h4>
      <div className="space-y-1">
        <MetricItem label="Total Requests" value={metrics?.total_requests ?? '-'} />
        <MetricItem
          label="Avg Latency"
          value={`${metrics?.average_latency_ms?.toFixed(2) ?? '-'} ms`}
        />

        {/* 30-second rolling window — only present on the Order Gateway */}
        {metrics?.rolling_window_avg_ms !== undefined && (
          <MetricItem
            label="30s Avg"
            value={
              <span className={isAlerting ? 'text-red-600 font-bold' : 'text-green-600'}>
                {metrics.rolling_window_avg_ms.toFixed(1)} ms{' '}
                {isAlerting ? '🔴' : '🟢'}
              </span>
            }
          />
        )}

        {/* Gateway-specific counters */}
        {metrics?.auth_failures !== undefined && (
          <MetricItem label="Auth Failures" value={metrics.auth_failures} />
        )}
        {metrics?.cache_short_circuits !== undefined && (
          <MetricItem label="Cache Short-Circuits" value={metrics.cache_short_circuits} />
        )}
        {metrics?.downstream_failures !== undefined && (
          <MetricItem label="Downstream Failures" value={metrics.downstream_failures} />
        )}

        {/* Stock-service-specific counters */}
        {metrics?.total_deductions !== undefined && (
          <MetricItem label="Total Deductions" value={metrics.total_deductions} />
        )}
        {metrics?.failed_deductions !== undefined && (
          <MetricItem label="Failed Deductions" value={metrics.failed_deductions} />
        )}
      </div>
    </div>
  );
};

const MetricsPanel = ({ services }) => {
  const gatewayService = services.find((s) => s.id === 'gateway');

  return (
    <div>
      {/* Top-of-panel alert banner — only visible when gateway latency is degraded */}
      {gatewayService && <GatewayAlertBanner gatewayUrl={gatewayService.url} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-8">
        {services.map((service) => (
          <ServiceMetricCard
            key={service.id}
            name={service.name}
            url={service.url}
          />
        ))}
      </div>
    </div>
  );
};

export default MetricsPanel;
