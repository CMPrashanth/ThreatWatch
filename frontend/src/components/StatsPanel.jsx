import React, { useEffect, useState } from 'react';
import { getStats } from '../services/api';
import { BarChart, Users, Zap, AlertCircle } from 'lucide-react';

const StatsPanel = ({ camera }) => {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!camera) {
      setStats(null);
      return;
    }

    const fetchStats = async () => {
      try {
        const statsData = await getStats(camera.id);
        setStats(statsData);
        setError(null);
      } catch (err) {
        setError('Could not load stats.');
        setStats(null);
      }
    };

    fetchStats(); // Fetch immediately on component mount
    const intervalId = setInterval(fetchStats, 5000); // And then every 5 seconds

    // Cleanup function to clear the interval
    return () => clearInterval(intervalId);
  }, [camera]); // Re-run effect if camera changes

  const StatCard = ({ icon, label, value, colorClass }) => (
    <div className={`flex items-center p-3 bg-gray-800 rounded-lg ${colorClass}`}>
      {icon}
      <div className="ml-3">
        <p className="text-gray-400 text-sm">{label}</p>
        <p className="font-bold text-xl text-white">{value}</p>
      </div>
    </div>
  );

  if (error) {
    return (
        <div className="bg-gray-950 rounded-2xl p-4 flex-1 shadow-lg flex items-center justify-center text-red-400">
            <AlertCircle className="mr-2" /> {error}
        </div>
    );
  }

  return (
    <div className="bg-gray-950 rounded-2xl p-4 flex-1 shadow-lg">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <BarChart className="mr-2 h-5 w-5" /> Real-time Stats
      </h3>
      <div className="space-y-3">
        <StatCard icon={<Users size={24} />} label="Active Trackers" value={stats?.active_trackers ?? '...'} />
        <StatCard icon={<Zap size={24} />} label="Processing FPS" value={stats?.fps?.toFixed(1) ?? '...'} />
        <div className="p-3 bg-gray-800 rounded-lg">
            <p className="text-gray-400 text-sm mb-2">Risk Distribution</p>
            <div className="flex justify-around text-center">
                <div>
                    <p className="font-bold text-lg text-green-400">{stats?.risk_distribution.low ?? '-'}</p>
                    <p className="text-xs text-gray-500">Low</p>
                </div>
                <div>
                    <p className="font-bold text-lg text-yellow-400">{stats?.risk_distribution.medium ?? '-'}</p>
                    <p className="text-xs text-gray-500">Medium</p>
                </div>
                <div>
                    <p className="font-bold text-lg text-orange-400">{stats?.risk_distribution.high ?? '-'}</p>
                    <p className="text-xs text-gray-500">High</p>
                </div>
                <div>
                    <p className="font-bold text-lg text-red-500">{stats?.risk_distribution.critical ?? '-'}</p>
                    <p className="text-xs text-gray-500">Critical</p>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default StatsPanel;
