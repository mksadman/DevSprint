import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import useWebSocket from '../hooks/useWebSocket';
import StatusStepper from '../components/status/StatusStepper';
import StatusBadge from '../components/status/StatusBadge';
import { getOrders } from '../api/orderApi';
import Loader from '../components/common/Loader';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { ROUTES, MENU_ITEMS } from '../utils/constants';

const DashboardPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const orderId = searchParams.get('orderId');
  
  const { status: wsStatus, isConnected } = useWebSocket(orderId);
  const [currentStatus, setCurrentStatus] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [manualOrderId, setManualOrderId] = useState('');

  // Fetch all orders on mount
  useEffect(() => {
    const fetchOrders = async () => {
      setLoading(true);
      try {
        const data = await getOrders();
        setOrders(data.orders || []);
      } catch (err) {
        console.error("Failed to fetch orders", err);
        setError('Failed to load order history.');
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, []);

  // Update status from WebSocket
  useEffect(() => {
    if (wsStatus) {
      setCurrentStatus(wsStatus);
      // Also update the status in the orders list
      setOrders(prevOrders => 
        prevOrders.map(order => 
          order.order_id === orderId 
            ? { ...order, status: wsStatus } 
            : order
        )
      );
    }
  }, [wsStatus, orderId]);

  // Pipeline statuses the stepper understands; gateway-only statuses
  // (CONFIRMED / RECEIVED) are normalised to PENDING as a safety fallback
  // until the first real pipeline event arrives via WebSocket.
  const PIPELINE_STATUSES = new Set(['PENDING', 'STOCK_VERIFIED', 'IN_KITCHEN', 'READY', 'CANCELLED']);

  // Set initial status when orderId changes or orders are loaded
  useEffect(() => {
    if (orderId && orders.length > 0) {
      const order = orders.find(o => o.order_id === orderId);
      if (order) {
        const pipelineStatus = PIPELINE_STATUSES.has(order.status) ? order.status : 'PENDING';
        setCurrentStatus(pipelineStatus);
      }
    }
  }, [orderId, orders]);

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (manualOrderId.trim()) {
      setSearchParams({ orderId: manualOrderId.trim() });
    }
  };

  const handleOrderClick = (id) => {
    setSearchParams({ orderId: id });
  };

  if (loading && orders.length === 0) return <div className="flex justify-center mt-20"><Loader /></div>;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-center text-gray-900">Order Dashboard</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Order List */}
        <div className="lg:col-span-1 bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden h-fit">
          <div className="p-4 border-b border-gray-100 bg-gray-50">
            <h2 className="text-lg font-semibold text-gray-800">Your Orders</h2>
          </div>
          
          <div className="divide-y divide-gray-100 max-h-150 overflow-y-auto">
            {orders.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <p>No orders found.</p>
                <Button 
                  className="mt-4 text-sm"
                  onClick={() => navigate(ROUTES.ORDER)}
                >
                  Place your first order
                </Button>
              </div>
            ) : (
              orders.map((order) => (
                <div 
                  key={order.order_id}
                  onClick={() => handleOrderClick(order.order_id)}
                  className={`p-4 cursor-pointer hover:bg-emerald-50 transition-colors ${
                    order.order_id === orderId ? 'bg-emerald-50 border-l-4 border-emerald-500' : ''
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-mono text-sm font-medium text-gray-600 truncate w-24" title={order.order_id}>
                      #{order.order_id.substring(0, 8)}...
                    </span>
                    <span className="text-xs text-gray-400">
                      {new Date(order.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="text-gray-800 font-medium">
                        {MENU_ITEMS.find(i => i.id === order.item_id)?.name || 'Item ' + order.item_id}
                      </span>
                      <span className="text-gray-500 text-sm ml-2">x{order.quantity}</span>
                    </div>
                    <StatusBadge status={order.status} size="sm" />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Order Details */}
        <div className="lg:col-span-2">
          {orderId ? (
            <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
              <div className="p-6 sm:p-8 border-b border-gray-100 bg-gray-50/50">
                <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
                  <div>
                    <span className="text-gray-500 text-sm uppercase tracking-wider font-semibold">Order ID</span>
                    <div className="font-mono text-lg font-bold text-gray-800 mt-1">{orderId}</div>
                  </div>
                  <div className="flex items-center bg-white px-4 py-2 rounded-full shadow-sm border border-gray-200">
                    <span className={`h-2.5 w-2.5 rounded-full mr-2 ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
                    <span className="text-sm font-medium text-gray-600">
                      {isConnected ? 'Live Updates Active' : 'Connecting...'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-8">
                <div className="flex justify-center mb-10">
                    <StatusBadge status={currentStatus} />
                </div>

                <StatusStepper currentStatus={currentStatus} />

                <div className="mt-12 text-center p-6 bg-emerald-50 rounded-lg border border-emerald-100">
                  <h3 className="text-lg font-semibold text-emerald-900 mb-2">
                    {currentStatus === 'READY' ? 'Ready for Pickup!' : 'Order in Progress'}
                  </h3>
                  <p className="text-emerald-700">
                    {currentStatus === 'READY' 
                      ? "Your delicious meal is waiting for you at the counter. Enjoy!"
                      : "Sit tight! We're preparing your order with care."}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-md border border-gray-100 p-8 text-center h-full flex flex-col justify-center items-center min-h-100">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Select an Order</h2>
              <p className="text-gray-500 mb-8 max-w-md">
                Select an order from the list on the left to view its real-time status details.
              </p>
              
              <div className="w-full max-w-md border-t border-gray-100 pt-8 mt-4">
                <p className="text-sm text-gray-400 mb-4 uppercase tracking-wider font-semibold">Or Track Manually</p>
                <form onSubmit={handleManualSubmit} className="flex gap-2">
                  <div className="grow">
                    <Input
                      name="manualOrderId"
                      value={manualOrderId}
                      onChange={(e) => setManualOrderId(e.target.value)}
                      placeholder="Enter Order ID manually..."
                    />
                  </div>
                  <Button type="submit" className="whitespace-nowrap h-10.5 mt-0.5">
                    Track
                  </Button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
