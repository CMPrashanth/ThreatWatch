import React from 'react';
import { X, ImageOff, Download } from 'lucide-react';

const SnapshotGalleryModal = ({ isOpen, onClose, incident }) => {
  if (!isOpen || !incident) return null;

  // --- FIXED: Directly use the snapshots array from the incident prop ---
  const snapshots = incident.snapshots || [];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-950 p-6 rounded-2xl shadow-lg w-full max-w-4xl relative flex flex-col max-h-[90vh]">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white">Snapshot Gallery</h2>
            <p className="text-sm text-gray-400">Incident at {new Date(incident.timestamp).toLocaleString()}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white"><X size={24} /></button>
        </div>
        <div className="flex-1 bg-gray-900 rounded-lg p-4 overflow-y-auto">
          {snapshots.length === 0 ? (
            <div className="flex flex-col justify-center items-center h-full text-gray-500">
              <ImageOff size={48} className="mb-4" />
              <p>No snapshots were automatically captured for this incident.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {snapshots.map(snapshot => (
                <div key={snapshot.id} className="group relative rounded-lg overflow-hidden border-2 border-transparent hover:border-indigo-500">
                  <img src={`http://localhost:8000/api/public/snapshot-proxy?url=${encodeURIComponent(snapshot.image_url)}`} alt={`Snapshot ${snapshot.id}`} className="w-full h-48 object-cover" />
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all flex items-center justify-center">
                    <a href={snapshot.image_url} download target="_blank" rel="noopener noreferrer" className="opacity-0 group-hover:opacity-100 p-2 bg-white text-black rounded-full transition-opacity">
                      <Download size={20} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SnapshotGalleryModal;
