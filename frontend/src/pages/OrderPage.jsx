import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { placeOrder } from '../api/orderApi';
import Button from '../components/common/Button';
import { ROUTES, MENU_ITEMS } from '../utils/constants';

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
        menu_item_id: id, 
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
  const totalPrice = Object.entries(selectedItems).reduce((total, [id, qty]) => {
    const item = MENU_ITEMS.find(i => i.id === id);
    return total + (item ? item.price * qty : 0);
  }, 0);

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-center">Place Your Order</h1>
      
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {MENU_ITEMS.map(item => (
          <div key={item.id} className="bg-white rounded-lg shadow-sm hover:shadow-xl hover:scale-105 transition-all duration-300 overflow-hidden border border-gray-100 p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-lg font-extrabold text-emerald-900">{item.name}</h3>
              <span className="bg-emerald-50 text-emerald-700 text-xs font-bold px-2 py-1 rounded-full border border-emerald-100">
                ${item.price.toFixed(2)}
              </span>
            </div>
            <p className="text-gray-500 text-xs mb-4 h-8 leading-snug">{item.description}</p>
            
            <div className="flex items-center justify-between pt-3 border-t border-gray-50">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Quantity</span>
              <div className="flex items-center space-x-2">
                <button 
                  className="w-7 h-7 rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 flex items-center justify-center transition-colors focus:outline-none shadow-sm"
                  onClick={() => handleQuantityChange(item.id, (selectedItems[item.id] || 0) - 1)}
                  disabled={!selectedItems[item.id]}
                >
                  -
                </button>
                <span className="w-6 text-center font-bold text-gray-800 text-sm">
                  {selectedItems[item.id] || 0}
                </span>
                <button 
                  className="w-7 h-7 rounded-full bg-emerald-600 text-white hover:bg-emerald-700 flex items-center justify-center transition-colors focus:outline-none shadow-md"
                  onClick={() => handleQuantityChange(item.id, (selectedItems[item.id] || 0) + 1)}
                >
                  +
                </button>
              </div>
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
