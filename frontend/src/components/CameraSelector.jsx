import React from 'react';
import { Video, PlayCircle, PauseCircle, StopCircle, Loader } from 'lucide-react';

const CameraSelector = ({ cameras, selectedCamera, setSelectedCamera, cameraStatuses, onStop }) => {
  const getStatusIcon = (camId) => {
    const status = cameraStatuses[camId];
    if (status === 'running') return <PlayCircle className="text-green-500" size={20} />;
    if (status === 'paused') return <PauseCircle className="text-yellow-500" size={20} />;
    if (status === undefined) return <Loader className="text-gray-500 animate-spin" size={20} />;
    return <StopCircle className="text-red-500" size={20} />;
  };

  return (
    <div className="bg-gray-950 rounded-2xl p-4 shadow-lg">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <Video className="mr-2 h-5 w-5" /> Cameras
      </h3>
      <div className="space-y-2">
        {cameras.map(cam => (
          <button
            key={cam.id}
            onClick={() => setSelectedCamera(cam)}
            className={`w-full text-left p-3 rounded-lg transition-all duration-200 flex items-center justify-between text-sm ${selectedCamera?.id === cam.id ? 'bg-indigo-600 font-semibold' : 'bg-gray-800 hover:bg-gray-700'}`}
          >
            <span>{cam.name}</span>
            <div className="flex items-center space-x-2">
              {getStatusIcon(cam.id)}
              {cameraStatuses[cam.id] && (
                <div
                  onClick={(e) => {
                    e.stopPropagation(); // Prevent the main button's onClick from firing
                    onStop(cam.id);
                  }}
                  className="text-xs bg-red-800 hover:bg-red-700 px-2 py-1 rounded cursor-pointer"
                >
                  Stop
                </div>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default CameraSelector;
