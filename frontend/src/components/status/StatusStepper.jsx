import React from 'react';
import { ORDER_STATUS } from '../../utils/constants';

const steps = [
  { key: ORDER_STATUS.PENDING, label: 'Pending' },
  { key: ORDER_STATUS.STOCK_VERIFIED, label: 'Stock Verified' },
  { key: ORDER_STATUS.IN_KITCHEN, label: 'In Kitchen' },
  { key: ORDER_STATUS.READY, label: 'Ready' },
];

const StatusStepper = ({ currentStatus }) => {
  const currentIndex = steps.findIndex(step => step.key === currentStatus);

  return (
    <div className="w-full py-6">
      <div className="flex items-center">
        {steps.map((step, index) => {
          const isCompleted = index <= currentIndex;
          const isLast = index === steps.length - 1;

          return (
            <React.Fragment key={step.key}>
              <div className="relative flex flex-col items-center text-blue-600">
                <div
                  className={`rounded-full transition-colors duration-500 ease-in-out h-12 w-12 flex items-center justify-center border-2 ${
                    isCompleted ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-300 text-gray-300'
                  }`}
                >
                  {index + 1}
                </div>
                <div className={`absolute top-0 mt-16 w-32 text-center text-xs font-medium uppercase ${isCompleted ? 'text-blue-600' : 'text-gray-500'}`}>
                  {step.label}
                </div>
              </div>
              {!isLast && (
                <div className={`flex-auto border-t-4 transition-colors duration-500 ease-in-out ${index < currentIndex ? 'border-blue-600' : 'border-gray-300'}`}></div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default StatusStepper;
