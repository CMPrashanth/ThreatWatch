import React, { useState } from 'react';
import { X, UploadCloud, Link as LinkIcon } from 'lucide-react';

const AddCameraModal = ({ isOpen, onClose, onSave, onUpload }) => {
  const [name, setName] = useState('');
  const [videoSource, setVideoSource] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [sourceType, setSourceType] = useState('url'); // 'url' or 'upload'
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSave = async () => {
    setIsLoading(true);
    if (sourceType === 'url') {
      await onSave({ name, video_source: videoSource });
    } else {
      await onUpload(name, selectedFile);
    }
    setIsLoading(false);
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
      <div className="bg-gray-950 p-8 rounded-2xl shadow-lg w-full max-w-lg relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-white"><X size={24} /></button>
        <h2 className="text-2xl font-bold text-white mb-6">Add New Camera</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Camera Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Lobby Entrance"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
            />
          </div>

          <div className="flex space-x-2 rounded-lg bg-gray-800 p-1">
            <button onClick={() => setSourceType('url')} className={`w-full py-2 rounded-md text-sm font-medium ${sourceType === 'url' ? 'bg-indigo-600 text-white' : 'text-gray-300'}`}>
              <LinkIcon className="inline-block mr-2" size={16}/>URL / Path
            </button>
            <button onClick={() => setSourceType('upload')} className={`w-full py-2 rounded-md text-sm font-medium ${sourceType === 'upload' ? 'bg-indigo-600 text-white' : 'text-gray-300'}`}>
              <UploadCloud className="inline-block mr-2" size={16}/>Upload Video
            </button>
          </div>

          {sourceType === 'url' ? (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Video Source</label>
              <input
                type="text"
                value={videoSource}
                onChange={(e) => setVideoSource(e.target.value)}
                placeholder="URL, IP address, or file path"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
              />
              <p className="text-xs text-gray-500 mt-1">For a webcam, use its index (e.g., '0' or '1').</p>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Video File</label>
              <input
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                className="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
              />
            </div>
          )}
        </div>

        <div className="mt-8 flex justify-end space-x-4">
          <button onClick={onClose} className="py-2 px-4 rounded-lg text-white bg-gray-700 hover:bg-gray-600">Cancel</button>
          <button onClick={handleSave} disabled={isLoading || !name || (sourceType === 'url' && !videoSource) || (sourceType === 'upload' && !selectedFile)} className="py-2 px-4 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400">
            {isLoading ? 'Saving...' : 'Save Camera'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddCameraModal;
