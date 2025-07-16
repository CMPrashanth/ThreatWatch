import React, { useEffect, useState, useCallback } from 'react';
import { getCameras, createCameraFromUrl, deleteCamera, updateCameraSettings, updateCurrentUser, getCurrentUser, uploadCamera, updateCameraZones } from '../services/api';
import { useAuth } from '../context/AuthContext.jsx';
import { toast } from 'sonner';
import { Loader, PlusCircle, Trash2, Edit, Map, User } from 'lucide-react';
import AddCameraModal from '../components/AddCameraModal.jsx';
import EditSettingsModal from '../components/EditSettingsModal.jsx';
import ZoneEditorModal from '../components/ZoneEditorModal.jsx';
import EditProfileModal from '../components/EditProfileModal.jsx';

const SettingsPage = () => {
  const { user: authUser, setAuthToken } = useAuth();
  const [fullUser, setFullUser] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(null);
  
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingSettingsFor, setEditingSettingsFor] = useState(null);
  const [editingZonesFor, setEditingZonesFor] = useState(null);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  // --- THIS IS THE FIX ---
  // The data loading logic is moved directly inside the useEffect hook.
  // This is a more standard pattern and avoids potential issues with useCallback dependencies.
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const [camerasData, userData] = await Promise.all([
          getCameras(),
          getCurrentUser()
        ]);
        setCameras(camerasData);
        setFullUser(userData);
      } catch (error) {
        toast.error(error.message || 'Failed to load page data.');
      } finally {
        setIsLoading(false);
      }
    };
    
    loadData();
  }, []); // The empty dependency array ensures this runs only once on mount.

  const handleCreateCamera = async (cameraData) => {
    try {
      const newCamera = await createCameraFromUrl(cameraData);
      setCameras([...cameras, newCamera]);
      toast.success('Camera added successfully!');
      setIsAddModalOpen(false);
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleUploadCamera = async (name, file) => {
    try {
      const newCamera = await uploadCamera(name, file);
      setCameras([...cameras, newCamera]);
      toast.success('Camera uploaded and added successfully!');
      setIsAddModalOpen(false);
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleUpdateSettings = async (cameraId, settingsData) => {
    try {
        const updatedCamera = await updateCameraSettings(cameraId, settingsData);
        setCameras(cameras.map(cam => cam.id === cameraId ? updatedCamera : cam));
        toast.success('Settings updated successfully!');
        setEditingSettingsFor(null);
    } catch (error) {
        toast.error(error.message);
    }
  };

  const handleUpdateZones = async (cameraId, zonesData) => {
    try {
      const updatedCamera = await updateCameraZones(cameraId, zonesData);
      setCameras(cameras.map(cam => cam.id === cameraId ? updatedCamera : cam));
      toast.success('Zones saved successfully!');
      setEditingZonesFor(null);
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleUpdateProfile = async (userData) => {
    try {
        const updatedUser = await updateCurrentUser(userData);
        setFullUser(updatedUser);
        toast.success('Profile updated successfully!');
        if (userData.password) {
            toast.info("Password changed. Please log in again.");
            setAuthToken(null);
        }
    } catch (error) {
        toast.error(error.message);
    }
  };

  const handleDelete = async (cameraId) => {
    if (window.confirm('Are you sure you want to delete this camera?')) {
        setIsDeleting(cameraId);
        try {
            await deleteCamera(cameraId);
            toast.success('Camera deleted successfully.');
            setCameras(cameras.filter(cam => cam.id !== cameraId));
        } catch (error) {
            toast.error(error.message);
        } finally {
            setIsDeleting(null);
        }
    }
  };
  
  const handleLinkSuccess = (updatedUser) => {
    setFullUser(updatedUser);
  };

  return (
    <>
      <AddCameraModal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} onSave={handleCreateCamera} onUpload={handleUploadCamera} />
      <EditSettingsModal isOpen={!!editingSettingsFor} onClose={() => setEditingSettingsFor(null)} onSave={handleUpdateSettings} camera={editingSettingsFor} />
      
      <ZoneEditorModal 
        key={editingZonesFor ? editingZonesFor.id : 'closed'}
        isOpen={!!editingZonesFor} 
        onClose={() => setEditingZonesFor(null)} 
        onSave={handleUpdateZones} 
        camera={editingZonesFor} 
      />
      
      <EditProfileModal 
        isOpen={isProfileModalOpen} 
        onClose={() => setIsProfileModalOpen(false)} 
        onSave={handleUpdateProfile} 
        user={fullUser}
        onLinkSuccess={handleLinkSuccess}
      />
      
      <div className="p-4 sm:p-6 lg:p-8 h-full flex flex-col bg-gray-900">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-white">System Settings</h1>
          <p className="text-gray-400">Manage your cameras and account details.</p>
        </header>

        <div className="bg-gray-950 rounded-2xl p-6 shadow-lg mb-6">
            <h2 className="text-xl font-semibold text-white mb-4">My Account</h2>
            <div className="flex justify-between items-center">
                <div>
                    <p className="font-medium text-white">{fullUser?.username || authUser?.sub}</p>
                    <p className="text-sm text-gray-400">{fullUser?.email}</p>
                </div>
                <button onClick={() => setIsProfileModalOpen(true)} className="flex items-center space-x-2 bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded-lg">
                    <User size={16} />
                    <span>Edit Profile</span>
                </button>
            </div>
        </div>

        <div className="flex-1 bg-gray-950 rounded-2xl p-6 shadow-lg">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-white">My Cameras</h2>
            <button onClick={() => setIsAddModalOpen(true)} className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2 px-4 rounded-lg">
              <PlusCircle size={20} />
              <span>Add New Camera</span>
            </button>
          </div>
          {isLoading ? (
            <div className="flex justify-center mt-8"><Loader className="animate-spin h-10 w-10 text-indigo-500" /></div>
          ) : (
            <div className="space-y-4">
              {cameras.map(cam => (
                <div key={cam.id} className="bg-gray-800 p-4 rounded-lg flex justify-between items-center">
                  <div>
                    <p className="font-bold text-white">{cam.name}</p>
                    <p className="text-sm text-gray-400 truncate max-w-md">{cam.video_source}</p>
                  </div>
                  <div className="flex items-center space-x-3">
                    <button onClick={() => setEditingZonesFor(cam)} className="flex items-center space-x-1 text-sm text-gray-300 hover:text-white"><Map size={16} /><span>Edit Zones</span></button>
                    <button onClick={() => setEditingSettingsFor(cam)} className="flex items-center space-x-1 text-sm text-gray-300 hover:text-white"><Edit size={16} /><span>Settings</span></button>
                    <button onClick={() => handleDelete(cam.id)} disabled={isDeleting === cam.id} className="p-2 rounded-full bg-gray-700 text-red-500 hover:bg-red-900 hover:text-red-400 disabled:bg-gray-600"><Trash2 size={16} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default SettingsPage;
