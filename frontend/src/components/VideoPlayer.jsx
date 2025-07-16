import React, { useEffect, useRef, useState } from 'react';
import { Wifi, WifiOff, Loader, Play, Pause, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const VideoPlayer = ({ camera, status, onAlert, onPause, onPlay }) => {
  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const token = localStorage.getItem('authToken');

  useEffect(() => {
    // Only connect if the analysis status is running or paused
    if (!camera || !token || (status !== 'running' && status !== 'paused')) {
      if (wsRef.current) wsRef.current.close();
      setConnectionStatus('disconnected');
      return;
    }

    setConnectionStatus('connecting');
    
    const wsUrl = `ws://localhost:8000/ws/video_feed/${camera.id}?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setConnectionStatus('connected');
    
    ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        const imageUrl = URL.createObjectURL(event.data);
        if (videoRef.current) videoRef.current.src = imageUrl;
      } else if (typeof event.data === 'string') {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'alert' && onAlert) onAlert(message.payload);
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      }
    };

    ws.onclose = () => setConnectionStatus('disconnected');
    ws.onerror = () => {
      setConnectionStatus('error');
      toast.error("Connection to video stream failed.");
    };

    return () => {
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        wsRef.current.close();
      }
    };
  }, [camera, token, onAlert, status]);

  const renderStatus = () => {
    switch (connectionStatus) {
      case 'connecting': return <div className="flex items-center text-yellow-400"><Loader size={16} className="animate-spin mr-2" />Connecting...</div>;
      case 'connected': return <div className="flex items-center text-green-400"><Wifi size={16} className="mr-2" />Connected</div>;
      case 'disconnected': return <div className="flex items-center text-gray-500"><WifiOff size={16} className="mr-2" />Not Watching</div>;
      case 'error': return <div className="flex items-center text-red-500"><AlertTriangle size={16} className="mr-2" />Error</div>;
      default: return null;
    }
  }

  return (
    <div className="h-full w-full flex flex-col bg-black rounded-lg overflow-hidden">
      <div className="p-3 bg-gray-900 flex justify-between items-center">
        <h4 className="font-semibold text-white">{camera?.name || 'No Camera Selected'}</h4>
        <div className="flex items-center space-x-4">
            {status && (
                <button onClick={status === 'running' ? onPause : onPlay} className="p-2 bg-gray-800 rounded-lg hover:bg-indigo-600">
                    {status === 'running' ? <Pause size={16} /> : <Play size={16} />}
                </button>
            )}
            <div className="text-sm">{renderStatus()}</div>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <img
          ref={videoRef}
          alt={connectionStatus !== 'connected' ? `Stream for ${camera?.name}` : ''}
          className="w-full h-full object-contain"
        />
      </div>
    </div>
  );
};

export default VideoPlayer;
