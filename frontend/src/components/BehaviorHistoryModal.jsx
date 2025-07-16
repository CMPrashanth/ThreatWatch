import React, { useEffect, useRef } from 'react';
import { X, ImageOff } from 'lucide-react';
import { toast } from 'sonner';

const BehaviorHistoryModal = ({ isOpen, onClose, incident }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!isOpen || !incident || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();

    // Use the first snapshot as the background
    const snapshotUrl = incident.snapshots?.[0]?.image_url;
    if (!snapshotUrl) {
      toast.error("No snapshot available to display path history.");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }
    
    img.src = `http://localhost:8000/api/public/snapshot-proxy?url=${encodeURIComponent(snapshotUrl)}`;
    img.crossOrigin = "Anonymous";

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      // --- FIXED: Directly use the path_data from the incident prop ---
      if (incident.path_data) {
        try {
          const pathPoints = JSON.parse(incident.path_data);
          if (pathPoints.length > 1) {
            ctx.strokeStyle = 'rgba(255, 255, 0, 0.9)';
            ctx.lineWidth = 3;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            ctx.beginPath();
            ctx.moveTo(pathPoints[0].x, pathPoints[0].y);
            for (let i = 1; i < pathPoints.length; i++) {
              ctx.lineTo(pathPoints[i].x, pathPoints[i].y);
            }
            ctx.stroke();

            ctx.beginPath();
            ctx.arc(pathPoints[0].x, pathPoints[0].y, 5, 0, 2 * Math.PI);
            ctx.fillStyle = 'rgba(0, 255, 0, 0.8)';
            ctx.fill();
          }
        } catch (error) {
          console.error("Failed to parse path data:", error);
          toast.error("Could not draw behavior path.");
        }
      }
    };
    img.onerror = () => {
        toast.error("Failed to load snapshot image.");
    }

  }, [isOpen, incident]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-950 p-6 rounded-2xl shadow-lg w-full max-w-5xl relative flex flex-col max-h-[95vh]">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white">Behavior History</h2>
            <p className="text-sm text-gray-400">Tracked path for incident at {new Date(incident.timestamp).toLocaleString()}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white"><X size={24} /></button>
        </div>
        <div className="flex-1 bg-black rounded-lg overflow-auto flex items-center justify-center">
          {incident.snapshots && incident.snapshots.length > 0 ? (
            <canvas ref={canvasRef} />
          ) : (
            <div className="text-gray-500 flex flex-col items-center">
                <ImageOff size={48} className="mb-4" />
                <p>No snapshot available for this incident.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BehaviorHistoryModal;
