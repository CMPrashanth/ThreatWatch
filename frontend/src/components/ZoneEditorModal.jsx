import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Trash2, PlusCircle, MousePointer, Check, ArrowLeft } from 'lucide-react';
import { getCameraSnapshot } from '../services/api';
import { toast } from 'sonner';

const ZoneEditorModal = ({ isOpen, onClose, onSave, camera }) => {
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const [zones, setZones] = useState({});
  const [currentPoints, setCurrentPoints] = useState([]);
  const [nextId, setNextId] = useState(1);
  const [isDrawing, setIsDrawing] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [isNaming, setIsNaming] = useState(false);
  const [newZoneName, setNewZoneName] = useState('');

  const drawPolygon = useCallback((ctx, points, fillColor, strokeColor) => {
    if (points.length === 0) return;
    ctx.fillStyle = fillColor;
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }, []);

  const getPolygonCenter = (points) => {
    if (points.length === 0) return { x: 0, y: 0 };
    const x = points.reduce((sum, p) => sum + p.x, 0) / points.length;
    const y = points.reduce((sum, p) => sum + p.y, 0) / points.length;
    return { x, y };
  };

  const redrawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img || !img.complete) return;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    Object.values(zones).forEach(zone => {
      drawPolygon(ctx, zone.points, 'rgba(0, 255, 0, 0.4)', 'white');
      const center = getPolygonCenter(zone.points);
      ctx.fillStyle = 'white';
      ctx.font = 'bold 14px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(zone.name, center.x, center.y);
    });

    if (currentPoints.length > 0) {
      drawPolygon(ctx, currentPoints, 'rgba(255, 255, 0, 0.5)', 'yellow');
    }
  }, [zones, currentPoints, drawPolygon]);

  // --- THIS IS THE FIX (Part 1) ---
  // This useEffect now ONLY handles initialization when the modal is opened for a specific camera.
  // It no longer depends on redrawCanvas, breaking the infinite loop.
  useEffect(() => {
    if (isOpen && camera) {
      setCurrentPoints([]);
      setIsDrawing(false);
      setIsNaming(false);

      if (camera.zones) {
        try {
          const parsedData = JSON.parse(camera.zones);
          const existingZones = parsedData.zones || parsedData;
          setZones(existingZones);
          const maxId = Object.keys(existingZones).length > 0 ? Math.max(...Object.keys(existingZones).map(Number)) : 0;
          setNextId(maxId + 1);
        } catch (e) {
          console.error("Failed to parse existing zones:", e);
          setZones({});
          setNextId(1);
        }
      } else {
        setZones({});
        setNextId(1);
      }
      
      const img = new Image();
      imageRef.current = img;
      
      getCameraSnapshot(camera.id)
        .then(blob => {
          img.src = URL.createObjectURL(blob);
          img.onload = () => {
            setImageDimensions({ width: img.width, height: img.height });
            const canvas = canvasRef.current;
            if (canvas) {
              canvas.width = img.width;
              canvas.height = img.height;
              // The redraw is now handled by the effect below, which triggers when the image is ready.
            }
          };
        })
        .catch(err => {
          toast.error("Failed to load camera snapshot for zone editing.");
          console.error(err);
        });
    }
  }, [isOpen, camera]);

  // --- THIS IS THE FIX (Part 2) ---
  // This separate useEffect is now solely responsible for redrawing the canvas
  // whenever the things that need to be drawn (zones, points, image) have changed.
  useEffect(() => {
    if (isOpen) {
      redrawCanvas();
    }
  }, [zones, currentPoints, imageDimensions, isOpen, redrawCanvas]);

  const handleCanvasClick = (e) => {
    if (!isDrawing || isNaming) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (canvas.width / rect.width);
    const y = (e.clientY - rect.top) * (canvas.height / rect.height);
    setCurrentPoints([...currentPoints, { x, y }]);
  };

  const handleFinishDrawing = () => {
    if (currentPoints.length < 3) {
      toast.error("A zone must have at least 3 points.");
      return;
    }
    setNewZoneName(`Zone ${nextId}`);
    setIsNaming(true);
  };

  const handleSaveZone = () => {
    if (!newZoneName.trim()) {
        toast.error("Zone name cannot be empty.");
        return;
    }
    const newZone = {
      id: nextId,
      name: newZoneName.trim(),
      points: currentPoints,
      access_level: 'restricted'
    };
    setZones(prevZones => ({ ...prevZones, [nextId]: newZone }));
    setNextId(prevId => prevId + 1);
    setCurrentPoints([]);
    setIsDrawing(false);
    setIsNaming(false);
    setNewZoneName('');
  };

  const handleDeleteZone = (idToDelete) => {
    setZones(prevZones => {
        const newZones = { ...prevZones };
        delete newZones[idToDelete];
        return newZones;
    });
  };

  const handleSave = () => {
    const dataToSave = {
      zones: zones,
      original_width: imageDimensions.width,
      original_height: imageDimensions.height
    };
    onSave(camera.id, dataToSave);
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-950 p-6 rounded-2xl shadow-lg w-full max-w-6xl relative flex flex-col max-h-[95vh]">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-white">Zone Editor: {camera?.name}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white"><X size={24} /></button>
        </div>
        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-6 overflow-hidden">
          <div className="md:col-span-2 bg-black rounded-lg overflow-auto flex items-center justify-center">
            <canvas ref={canvasRef} onClick={handleCanvasClick} className={isDrawing ? 'cursor-crosshair' : 'cursor-default'} />
          </div>
          <div className="flex flex-col space-y-4">
            <div className="flex-1 bg-gray-900 p-4 rounded-lg overflow-y-auto">
              <h3 className="font-semibold mb-2">Defined Zones</h3>
              <div className="space-y-2">
                {Object.values(zones).length === 0 ? (
                  <p className="text-sm text-gray-500">No zones defined yet.</p>
                ) : (
                  Object.values(zones).map(zone => (
                    <div key={zone.id} className="flex justify-between items-center bg-gray-800 p-2 rounded">
                      <span>{zone.name}</span>
                      <button onClick={() => handleDeleteZone(zone.id)} className="text-red-500 hover:text-red-400"><Trash2 size={16}/></button>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="bg-gray-900 p-4 rounded-lg">
              <h3 className="font-semibold mb-2">Actions</h3>
              {!isDrawing ? (
                <button onClick={() => setIsDrawing(true)} className="w-full flex items-center justify-center py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700">
                  <PlusCircle size={16} className="mr-2"/> Add New Zone
                </button>
              ) : isNaming ? (
                <div className="space-y-3">
                    <label className="block text-sm font-medium text-gray-300">Enter Zone Name</label>
                    <input
                        type="text"
                        value={newZoneName}
                        onChange={(e) => setNewZoneName(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                        autoFocus
                    />
                    <div className="flex space-x-2">
                        <button onClick={() => setIsNaming(false)} className="w-full py-2 px-4 rounded-lg text-white bg-gray-600 hover:bg-gray-500 flex items-center justify-center"><ArrowLeft size={16} className="mr-2"/> Back</button>
                        <button onClick={handleSaveZone} className="w-full py-2 px-4 rounded-lg text-white bg-green-600 hover:bg-green-700 flex items-center justify-center"><Check size={16} className="mr-2"/>Save Zone</button>
                    </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-yellow-400 flex items-center"><MousePointer size={16} className="mr-2"/> Click on the image to add points.</p>
                  <button onClick={handleFinishDrawing} className="w-full py-2 px-4 rounded-lg text-white bg-green-600 hover:bg-green-700">Finish Drawing</button>
                  <button onClick={() => { setIsDrawing(false); setCurrentPoints([]); }} className="w-full py-2 px-4 rounded-lg text-white bg-gray-600 hover:bg-gray-500">Cancel</button>
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="mt-6 flex justify-end space-x-4">
          <button onClick={onClose} className="py-2 px-4 rounded-lg text-white bg-gray-700 hover:bg-gray-600">Cancel</button>
          <button onClick={handleSave} className="py-2 px-6 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700">Save All Zones</button>
        </div>
      </div>
    </div>
  );
};

export default ZoneEditorModal;
