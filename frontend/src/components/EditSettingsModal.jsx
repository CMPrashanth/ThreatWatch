import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const EditSettingsModal = ({ isOpen, onClose, onSave, camera }) => {
  const [settings, setSettings] = useState({
    sensitivity: 'medium',
    loitering_threshold: 10.0,
    risk_alert_threshold: 20.0,
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // When the modal is opened, populate its state with the current camera's settings
    if (camera) {
      setSettings({
        sensitivity: camera.sensitivity || 'medium',
        loitering_threshold: camera.loitering_threshold || 10.0,
        risk_alert_threshold: camera.risk_alert_threshold || 20.0,
      });
    }
  }, [camera]);

  if (!isOpen || !camera) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    setIsLoading(true);
    await onSave(camera.id, settings);
    setIsLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
      <div className="bg-gray-950 p-8 rounded-2xl shadow-lg w-full max-w-lg relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-white">
          <X size={24} />
        </button>
        <h2 className="text-2xl font-bold text-white mb-2">Edit Settings</h2>
        <p className="text-gray-400 mb-6">For camera: <span className="font-semibold text-indigo-400">{camera.name}</span></p>
        
        <div className="space-y-6">
          <div>
            <label htmlFor="sensitivity" className="block text-sm font-medium text-gray-300 mb-1">Detection Sensitivity</label>
            <select id="sensitivity" name="sensitivity" value={settings.sensitivity} onChange={handleChange} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-indigo-500 focus:border-indigo-500">
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
          <div>
            <label htmlFor="loitering_threshold" className="block text-sm font-medium text-gray-300 mb-1">Loitering Threshold (seconds)</label>
            <input id="loitering_threshold" name="loitering_threshold" type="number" value={settings.loitering_threshold} onChange={handleChange} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-indigo-500 focus:border-indigo-500" />
          </div>
          <div>
            <label htmlFor="risk_alert_threshold" className="block text-sm font-medium text-gray-300 mb-1">Risk Alert Threshold (1-100)</label>
            <input id="risk_alert_threshold" name="risk_alert_threshold" type="number" value={settings.risk_alert_threshold} onChange={handleChange} className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-indigo-500 focus:border-indigo-500" />
          </div>
        </div>

        <div className="mt-8 flex justify-end space-x-4">
          <button onClick={onClose} className="py-2 px-4 rounded-lg text-white bg-gray-700 hover:bg-gray-600">
            Cancel
          </button>
          <button onClick={handleSave} disabled={isLoading} className="py-2 px-4 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400">
            {isLoading ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditSettingsModal;
