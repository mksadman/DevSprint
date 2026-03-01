import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import useWebSocket from '../hooks/useWebSocket';
import StatusStepper from '../components/status/StatusStepper';
import StatusBadge from '../components/status/StatusBadge';
import { getOrder } from '../api/orderApi';
import Loader from '../components/common/Loader';

const DashboardPage = () => {
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('orderId');
  const { status: wsStatus, isConnected } = useWebSocket(orderId);
  const [currentStatus, setCurrentStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Initial fetch of order status
  useEffect(() => {
    if (!orderId) {
      setError('No Order ID provided.');
      setLoading(false);
      return;
    }

    const fetchOrder = async () => {
      try {
        const order = await getOrder(orderId);
        setCurrentStatus(order.status);
      } catch (err) {
        console.error("Failed to fetch order", err);
        setError('Failed to load order details.');
      } finally {
        setLoading(false);
      }
    };

    fetchOrder();
  }, [orderId]);

  // Update status from WebSocket
  useEffect(() => {
    if (wsStatus) {
      setCurrentStatus(wsStatus);
    }
  }, [wsStatus]);

  if (loading) return <div className="flex justify-center mt-10"><Loader /></div>;
  if (error) return <div className="text-center mt-10 text-red-600">{error}</div>;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-4 text-center">Order Status</h1>
      
      <div className="max-w-3xl mx-auto bg-white rounded shadow-lg p-8">
        <div className="flex justify-between items-center mb-8 border-b pb-4">
          <div>
            <span className="text-gray-500 text-sm">Order ID</span>
            <div className="font-mono text-lg font-bold">#{orderId}</div>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-gray-500 text-sm mb-1">Live Status</span>
            <div className="flex items-center">
              <span className={`h-2 w-2 rounded-full mr-2 ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              <span className="text-sm text-gray-600">{isConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
          </div>
        </div>

        <div className="flex justify-center mb-8">
            <StatusBadge status={currentStatus} />
        </div>

        <StatusStepper currentStatus={currentStatus} />

        <div className="mt-8 text-center text-gray-500 text-sm">
          {currentStatus === 'READY' 
            ? "Your order is ready! Please pick it up at the counter."
            : "We are processing your order. Please wait."}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
