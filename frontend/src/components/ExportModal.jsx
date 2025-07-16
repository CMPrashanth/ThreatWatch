import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const ExportModal = ({ isOpen, onClose, onExport, cameras }) => {
  const today = new Date().toISOString().split('T')[0];
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(today);
  const [cameraId, setCameraId] = useState(''); // Empty string for "All Cameras"
  const [isLoading, setIsLoading] = useState(false);
  const [dateError, setDateError] = useState(''); // State for validation error

  // Real-time validation as dates change
  useEffect(() => {
    if (new Date(endDate) < new Date(startDate)) {
      setDateError('End date cannot be earlier than start date.');
    } else {
      setDateError('');
    }
  }, [startDate, endDate]);

  if (!isOpen) return null;

  const handleExport = async () => {
    // Final check before exporting
    if (dateError) {
      return; // Prevent export if there's a date error
    }
    setIsLoading(true);
    await onExport({
      start_date: startDate,
      end_date: endDate,
      camera_id: cameraId || null, // Send null if "All Cameras" is selected
    });
    setIsLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
      <div className="bg-gray-950 p-8 rounded-2xl shadow-lg w-full max-w-md relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-white"><X size={24} /></button>
        <h2 className="text-2xl font-bold text-white mb-6">Export Incident Data</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Start Date</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-indigo-500 focus:border-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">End Date</label>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-indigo-500 focus:border-indigo-500" />
          </div>
           {dateError && <p className="text-sm text-red-500">{dateError}</p>}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Camera</label>
            <select value={cameraId} onChange={e => setCameraId(e.target.value)} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-indigo-500 focus:border-indigo-500">
              <option value="">All Cameras</option>
              {cameras.map(cam => <option key={cam.id} value={cam.id}>{cam.name}</option>)}
            </select>
          </div>
        </div>

        <div className="mt-8 flex justify-end space-x-4">
          <button onClick={onClose} className="py-2 px-4 rounded-lg text-white bg-gray-700 hover:bg-gray-600">Cancel</button>
          <button onClick={handleExport} disabled={isLoading || !!dateError} className="py-2 px-4 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 disabled:cursor-not-allowed">
            {isLoading ? 'Exporting...' : 'Export to CSV'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExportModal;
