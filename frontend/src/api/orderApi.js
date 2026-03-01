import axiosClient from './axiosClient';

export const placeOrder = async (items) => {
  // Backend expects a single item per request in the current hackathon setup
  const orderId = crypto.randomUUID();
  
  // For this MVP, let's just place the first item found. 
  const firstItem = items[0];
  
  const response = await axiosClient.post('/order', { 
    order_id: orderId,
    item_id: String(firstItem.menu_item_id), // Backend expects string
    quantity: firstItem.quantity
  });
  return response.data;
};

export const getOrder = async (orderId) => {
  // This endpoint might not exist in backend, but let's keep it for direct access if needed
  // or if we add it later. For now, the dashboard will primarily use getOrders (list)
  // or rely on WebSocket for single order updates if we already have the ID.
  // Actually, for "Track Order" with manual ID, we might need a specific endpoint.
  // Since we added GET /orders (list), we can also filter client side if needed, 
  // OR strictly we should add GET /order/{id} to backend if we want to track ANY order.
  // But for "My Orders", list is fine.
  const response = await axiosClient.get(`/orders/${orderId}`);
  return response.data;
};

export const getOrders = async () => {
  const response = await axiosClient.get('/orders');
  return response.data;
};
