import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { placeOrder } from '../api/orderApi';
import Button from '../components/common/Button';
import { ROUTES } from '../utils/constants';

const MENU_ITEMS = [
  { id: 1, name: 'Burger', price: 5.99 },
  { id: 2, name: 'Pizza', price: 8.99 },
  { id: 3, name: 'Salad', price: 4.99 },
  { id: 4, name: 'Fries', price: 2.99 },
  { id: 5, name: 'Soda', price: 1.99 },
];

const OrderPage = () => {
  const [selectedItems, setSelectedItems] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleQuantityChange = (itemId, quantity) => {
    if (quantity < 0) return;
    setSelectedItems(prev => ({
      ...prev,
      [itemId]: quantity
    }));
  };

  const handlePlaceOrder = async () => {
    const items = Object.entries(selectedItems)
      .filter(([_, quantity]) => quantity > 0)
      .map(([id, quantity]) => ({ 
        menu_item_id: parseInt(id), 
        quantity 
      }));

    if (items.length === 0) {
      setError('Please select at least one item.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await placeOrder(items);
      // Assuming response contains order_id
      const orderId = response.order_id || response.id; 
      navigate(`${ROUTES.DASHBOARD}?orderId=${orderId}`);
    } catch (err) {
      if (err.response && err.response.status === 409) {
        setError('One or more items are out of stock.');
      } else {
        setError('Failed to place order. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const totalItems = Object.values(selectedItems).reduce((a, b) => a + b, 0);

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-center">Place Your Order</h1>
      
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {MENU_ITEMS.map(item => (
          <div key={item.id} className="bg-white rounded shadow p-4 flex flex-col justify-between">
            <div>
              <h3 className="text-xl font-semibold">{item.name}</h3>
              <p className="text-gray-600">${item.price.toFixed(2)}</p>
            </div>
            <div className="mt-4 flex items-center justify-end">
              <button 
                className="px-3 py-1 bg-gray-200 rounded-l hover:bg-gray-300"
                onClick={() => handleQuantityChange(item.id, (selectedItems[item.id] || 0) - 1)}
              >
                -
              </button>
              <span className="px-4 py-1 bg-gray-100 border-t border-b border-gray-200">
                {selectedItems[item.id] || 0}
              </span>
              <button 
                className="px-3 py-1 bg-gray-200 rounded-r hover:bg-gray-300"
                onClick={() => handleQuantityChange(item.id, (selectedItems[item.id] || 0) + 1)}
              >
                +
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-col items-center">
        <div className="text-xl mb-4">
          Total Items: <span className="font-bold">{totalItems}</span>
        </div>
        <Button onClick={handlePlaceOrder} loading={loading} disabled={totalItems === 0} className="w-full max-w-md text-lg">
          Place Order
        </Button>
      </div>
    </div>
  );
};

export default OrderPage;
