import axiosClient from './axiosClient';

export const placeOrder = async (items) => {
  const response = await axiosClient.post('/orders', { items });
  return response.data;
};

export const getOrder = async (orderId) => {
  const response = await axiosClient.get(`/orders/${orderId}`);
  return response.data;
};
