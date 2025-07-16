import React, { useEffect, useState, useCallback } from 'react';
import { getCameras, getIncidents, resolveIncident, exportIncidents } from '../services/api';
import { toast } from 'sonner';
import { Loader, ShieldAlert, FileDown, Camera, Eye, Footprints, Megaphone } from 'lucide-react';
import SnapshotGalleryModal from '../components/SnapshotGalleryModal';
import ExportModal from '../components/ExportModal';
import BehaviorHistoryModal from '../components/BehaviorHistoryModal';
import { useNavigate } from 'react-router-dom';

const IncidentsPage = () => {
  const [cameras, setCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [incidents, setIncidents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(null);
  
  const [selectedIncidentForModal, setSelectedIncidentForModal] = useState(null);

  const [isSnapshotModalOpen, setIsSnapshotModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const camerasData = await getCameras();
        setCameras(camerasData);
        if (camerasData.length > 0) {
          setSelectedCameraId(camerasData[0].id);
        } else {
          setIsLoading(false);
        }
      } catch (error) {
        toast.error(error.message || 'Failed to load cameras.');
        setIsLoading(false);
      }
    };
    fetchCameras();
  }, []);

  useEffect(() => {
    if (!selectedCameraId) return;

    const fetchIncidents = async () => {
      setIsLoading(true);
      try {
        const incidentsData = await getIncidents(selectedCameraId);
        setIncidents(incidentsData);
      } catch (error) {
        toast.error(error.message || 'Failed to load incidents.');
        setIncidents([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchIncidents();
  }, [selectedCameraId]);

  const openSnapshotModal = (incident) => {
    setSelectedIncidentForModal(incident);
    setIsSnapshotModalOpen(true);
  };

  const openHistoryModal = (incident) => {
    setSelectedIncidentForModal(incident);
    setIsHistoryModalOpen(true);
  };

  const handleFileComplaint = (incident) => {
    navigate('/complaint', { 
      state: { 
        incidentId: incident.id,
        threatType: incident.primary_threat,
        timestamp: incident.timestamp,
        snapshotUrl: incident.snapshots?.[0]?.image_url 
      } 
    });
  };

  const handleResolve = async (incidentId) => {
    setIsUpdating(incidentId);
    try {
      await resolveIncident(incidentId);
      setIncidents(incidents.map(inc => 
        inc.id === incidentId ? { ...inc, resolved: true } : inc
      ));
      toast.success('Incident marked as resolved.');
    } catch (error) {
      toast.error(error.message || 'Failed to update incident.');
    } finally {
      setIsUpdating(null);
    }
  };

  const handleExport = async (params) => {
    try {
        const blob = await exportIncidents(params);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `incidents_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        toast.success("Export started successfully.");
        setIsExportModalOpen(false);
    } catch (error) {
        toast.error("Failed to export data.");
    }
  };

  return (
    <>
      <SnapshotGalleryModal isOpen={isSnapshotModalOpen} onClose={() => setIsSnapshotModalOpen(false)} incident={selectedIncidentForModal} />
      <ExportModal isOpen={isExportModalOpen} onClose={() => setIsExportModalOpen(false)} onExport={handleExport} cameras={cameras} />
      <BehaviorHistoryModal isOpen={isHistoryModalOpen} onClose={() => setIsHistoryModalOpen(false)} incident={selectedIncidentForModal} />
      
      <div className="p-4 sm:p-6 lg:p-8 h-full flex flex-col bg-gray-900">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-white">Incidents Log</h1>
          <p className="text-gray-400">Review and manage all detected security alerts.</p>
        </header>

        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center space-x-4">
            <label htmlFor="camera-select" className="text-sm font-medium text-gray-300">Filter by Camera:</label>
            <select id="camera-select" value={selectedCameraId} onChange={(e) => setSelectedCameraId(e.target.value)} className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-full p-2.5" disabled={cameras.length === 0}>
              {cameras.map(cam => (<option key={cam.id} value={cam.id}>{cam.name}</option>))}
            </select>
          </div>
          <button onClick={() => setIsExportModalOpen(true)} className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2 px-4 rounded-lg text-sm">
            <FileDown size={16} />
            <span>Export Data</span>
          </button>
        </div>

        <div className="flex-1 bg-gray-950 rounded-2xl overflow-auto shadow-lg">
          {isLoading ? (
            <div className="flex items-center justify-center h-full"><Loader className="animate-spin h-12 w-12 text-indigo-500" /></div>
          ) : incidents.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
              <ShieldAlert size={64} className="mb-4" />
              <h3 className="text-xl font-semibold text-white">No Incidents Found</h3>
              <p>No threats have been detected for the selected camera.</p>
            </div>
          ) : (
            <table className="w-full text-sm text-left text-gray-400">
              <thead className="text-xs text-gray-400 uppercase bg-gray-800 sticky top-0">
                <tr>
                  <th scope="col" className="px-6 py-3">Timestamp</th>
                  <th scope="col" className="px-6 py-3">Threat Type</th>
                  <th scope="col" className="px-6 py-3">Risk Score</th>
                  <th scope="col" className="px-6 py-3">Status</th>
                  <th scope="col" className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map(inc => (
                  <tr key={inc.id} className="bg-gray-950 border-b border-gray-800 hover:bg-gray-800">
                    <td className="px-6 py-4">{new Date(inc.timestamp).toLocaleString()}</td>
                    <td className="px-6 py-4 font-medium text-red-400">{inc.primary_threat}</td>
                    <td className="px-6 py-4">{inc.risk_score.toFixed(1)}</td>
                    <td className="px-6 py-4"><span className={`px-2 py-1 text-xs font-medium rounded-full ${inc.resolved ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300'}`}>{inc.resolved ? 'Resolved' : 'Unresolved'}</span></td>
                    <td className="px-6 py-4 flex items-center space-x-3">
                      <button onClick={() => openSnapshotModal(inc)} className="text-blue-400 hover:text-blue-300" title="View Snapshots"><Camera size={16} /></button>
                      <button onClick={() => openHistoryModal(inc)} className="text-purple-400 hover:text-purple-300" title="View Behavior Path"><Footprints size={16} /></button>
                      {!inc.resolved && (<button onClick={() => handleResolve(inc.id)} disabled={isUpdating === inc.id} className="text-green-400 hover:text-green-300 disabled:text-gray-500" title="Mark as Resolved">{isUpdating === inc.id ? <Loader size={16} className="animate-spin" /> : <Eye size={16} />}</button>)}
                      <button onClick={() => handleFileComplaint(inc)} className="text-orange-400 hover:text-orange-300" title="File Complaint"><Megaphone size={16} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
};

export default IncidentsPage;
