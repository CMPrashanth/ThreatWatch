import React, { useEffect, useState, useCallback } from 'react';
import { getCameras, getCamerasStatus, startAnalysis, stopAnalysis, playAnalysis, pauseAnalysis } from '../services/api.js';
import { toast } from 'sonner';
import { Loader, Camera } from 'lucide-react';

import CameraSelector from '../components/CameraSelector.jsx';
import VideoPlayer from '../components/VideoPlayer.jsx';
import StatsPanel from '../components/StatsPanel.jsx';

const DashboardPage = () => {
  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [cameraStatuses, setCameraStatuses] = useState({});
  const [isLoading, setIsLoading] = useState(true);

  const fetchAllDataAndStartCameras = useCallback(async () => {
    // Set loading only on the very first fetch
    setIsLoading(true);
    try {
      const camerasData = await getCameras();
      setCameras(camerasData);
      
      const statusesData = await getCamerasStatus();
      setCameraStatuses(statusesData);

      // Identify which cameras are not yet running
      const camerasToStart = camerasData.filter(cam => !statusesData[cam.id]);

      if (camerasToStart.length > 0) {
        // Attempt to start all non-running cameras in parallel
        await Promise.allSettled(
          camerasToStart.map(cam => {
            console.log(`Auto-starting analysis for camera: ${cam.name}`);
            return startAnalysis(cam.id).catch(err => {
              // This handles the race condition where a start command is sent twice.
              // We only show an error if it's for a reason other than the camera already running.
              if (!err.message.includes("already running")) {
                  toast.error(`Failed to start ${cam.name}: ${err.message}`);
              }
            });
          })
        );
        
        // After attempting to start, fetch the statuses again to get the final, correct state.
        const finalStatuses = await getCamerasStatus();
        setCameraStatuses(finalStatuses);
      }
    } catch (error) {
      toast.error(error.message || 'Failed to load dashboard data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllDataAndStartCameras();
    // Periodically refresh statuses to keep the UI in sync
    const interval = setInterval(() => {
        getCamerasStatus().then(setCameraStatuses).catch(console.error);
    }, 5000); 
    return () => clearInterval(interval);
  }, [fetchAllDataAndStartCameras]);

  const handleApiCall = async (apiFunc, cameraId, successMessage) => {
    try {
      await apiFunc(cameraId);
      toast.success(successMessage);
      // Refresh statuses immediately after an action
      getCamerasStatus().then(setCameraStatuses);
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleStop = (cameraId) => handleApiCall(stopAnalysis, cameraId, 'Analysis stopped.');
  const handlePause = (cameraId) => handleApiCall(pauseAnalysis, cameraId, 'Analysis paused.');
  const handlePlay = (cameraId) => handleApiCall(playAnalysis, cameraId, 'Analysis resumed.');

  const handleNewAlert = useCallback((alertPayload) => {
    toast.error(`Threat Detected: ${alertPayload.threat_type}`, {
      description: `Camera: ${alertPayload.camera_name} | Risk Score: ${alertPayload.risk_score.toFixed(1)}`,
      duration: 10000,
    });
  }, []);

  if (isLoading) {
    return (
        <div className="flex items-center justify-center h-full">
            <Loader className="animate-spin h-12 w-12 text-indigo-500" />
        </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 h-full flex flex-col bg-gray-900">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400">Real-time threat monitoring overview.</p>
      </header>
      
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-gray-950 rounded-2xl p-1 flex flex-col shadow-lg">
          {selectedCamera ? (
            <VideoPlayer 
              camera={selectedCamera} 
              status={cameraStatuses[selectedCamera.id]}
              onAlert={handleNewAlert} 
              onPause={() => handlePause(selectedCamera.id)}
              onPlay={() => handlePlay(selectedCamera.id)}
            />
          ) : (
            <div className="flex-1 bg-black rounded-lg flex flex-col items-center justify-center text-gray-500">
                <Camera size={48} className="mb-4" />
                <h3 className="text-lg font-semibold">No Camera Selected</h3>
                <p className="text-sm">Select a camera from the list to view its live feed.</p>
            </div>
          )}
        </div>
        <div className="flex flex-col space-y-6">
          <CameraSelector 
            cameras={cameras}
            selectedCamera={selectedCamera}
            setSelectedCamera={setSelectedCamera}
            cameraStatuses={cameraStatuses}
            onStop={handleStop}
          />
          <StatsPanel camera={selectedCamera} />
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
