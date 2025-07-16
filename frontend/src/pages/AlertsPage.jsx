import React, { useEffect, useState } from 'react';
import { getAlerts } from '../services/api';
import { toast } from 'sonner';
import { Loader, ShieldCheck, Siren, Megaphone } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const AlertsPage = () => {
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await getAlerts();
        setAlerts(data.alerts);
      } catch (error) {
        toast.error("Failed to load alerts.");
        console.error("Error fetching alerts:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAlerts();
  }, []);

  const handleFileComplaint = (alert) => {
    navigate('/complaint', { 
      state: { 
        incidentId: alert.id,
        threatType: alert.threat_type,
        timestamp: alert.timestamp,
        snapshotUrl: alert.snapshot_url
      } 
    });
  };

  const AlertCard = ({ alert }) => (
    <div className="bg-gray-950 rounded-2xl shadow-lg overflow-hidden flex flex-col">
      {alert.snapshot_url ? (
        <img 
          src={`http://localhost:8000/api/public/snapshot-proxy?url=${encodeURIComponent(alert.snapshot_url)}`} 
          alt={`Snapshot for alert ${alert.id}`} 
          className="w-full h-48 object-cover"
        />
      ) : (
        <div className="w-full h-48 bg-black flex items-center justify-center text-gray-500">
          <Siren size={48} />
        </div>
      )}
      <div className="p-4 flex-1 flex flex-col">
        <h3 className="text-lg font-bold text-red-500 capitalize mb-2">{alert.threat_type.replace(/_/g, ' ')}</h3>
        <div className="text-sm text-gray-300 space-y-1">
            <p><span className="font-semibold text-gray-500">Camera:</span> {alert.camera_name}</p>
            <p><span className="font-semibold text-gray-500">Risk Score:</span> {alert.risk_score.toFixed(1)}</p>
            <p><span className="font-semibold text-gray-500">Timestamp:</span> {new Date(alert.timestamp).toLocaleString()}</p>
        </div>
        <div className="mt-auto pt-4 flex justify-between items-center">
             <span className={`px-3 py-1 text-xs font-medium rounded-full ${alert.resolved ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300'}`}>
                {alert.resolved ? 'Resolved' : 'Unresolved'}
            </span>
            <button onClick={() => handleFileComplaint(alert)} className="text-orange-400 hover:text-orange-300" title="File Complaint">
                <Megaphone size={16} />
            </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="p-4 sm:p-6 lg:p-8 h-full flex flex-col bg-gray-900">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-white flex items-center">
          <Siren className="mr-4 text-red-500" /> System Alerts
        </h1>
        <p className="text-gray-400">A log of all incidents that triggered a system notification.</p>
      </header>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full"><Loader className="animate-spin h-12 w-12 text-indigo-500" /></div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
            <ShieldCheck size={64} className="mb-4 text-green-500" />
            <h3 className="text-xl font-semibold text-white">All Clear</h3>
            <p>No incidents have triggered a notification yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {alerts.map((alert) => (
              <AlertCard key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertsPage;
