import React from 'react';
import { ORDER_STATUS } from '../../utils/constants';

const StatusBadge = ({ status }) => {
  let colorClass = 'bg-gray-200 text-gray-800';

  switch (status) {
    case ORDER_STATUS.PENDING:
      colorClass = 'bg-yellow-200 text-yellow-800';
      break;
    case ORDER_STATUS.STOCK_VERIFIED:
      colorClass = 'bg-blue-200 text-blue-800';
      break;
    case ORDER_STATUS.IN_KITCHEN:
      colorClass = 'bg-purple-200 text-purple-800';
      break;
    case ORDER_STATUS.READY:
      colorClass = 'bg-green-200 text-green-800';
      break;
    case ORDER_STATUS.CANCELLED:
      colorClass = 'bg-red-200 text-red-800';
      break;
    default:
      break;
  }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${colorClass}`}>
      {status ? status.replace('_', ' ') : 'UNKNOWN'}
    </span>
  );
};

export default StatusBadge;
