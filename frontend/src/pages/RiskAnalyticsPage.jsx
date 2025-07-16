import React, { useEffect, useState } from 'react';
import { getAnalyticsData } from '../services/api';
import { toast } from 'sonner';
import { Loader, PieChart as PieChartIcon, BarChart2 } from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// Consistent color scheme
const COLORS = ['#EF4444', '#F59E0B', '#8B5CF6', '#3B82F6', '#10B981'];

const ThemedTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="p-2 bg-gray-700 border border-gray-600 rounded shadow-lg text-white">
        <p className="label">{`${label}`}</p>
        {payload.map((p, index) => (
            <p key={index} style={{ color: p.color }}>{`${p.name}: ${p.value}`}</p>
        ))}
      </div>
    );
  }
  return null;
};

const RiskAnalyticsPage = () => {
    const [data, setData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const analyticsData = await getAnalyticsData();
                setData(analyticsData);
            } catch (error) {
                toast.error("Failed to load analytics data.");
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, []);

    if (isLoading) {
        return <div className="flex items-center justify-center h-full"><Loader className="animate-spin h-12 w-12 text-indigo-500" /></div>;
    }
    
    if (!data) {
        return <div className="flex items-center justify-center h-full text-red-500">Could not load data.</div>;
    }

    return (
        <div className="p-4 sm:p-6 lg:p-8 h-full flex flex-col bg-gray-900">
            <header className="mb-6">
                <h1 className="text-3xl font-bold text-white">Risk Analytics</h1>
                <p className="text-gray-400">An overview of detected threats and zone activity.</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-gray-950 rounded-2xl p-6 shadow-lg">
                    <h3 className="text-xl font-semibold text-white mb-4 flex items-center"><PieChartIcon className="mr-3 text-indigo-400"/>Threat Frequency by Type</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                            <Pie data={data.threat_frequency} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                                {data.threat_frequency.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip content={<ThemedTooltip />} />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                <div className="bg-gray-950 rounded-2xl p-6 shadow-lg">
                    <h3 className="text-xl font-semibold text-white mb-4 flex items-center"><BarChart2 className="mr-3 text-indigo-400"/>Zone-wise Threat Summary</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={data.zone_summary}>
                            <XAxis dataKey="zone_name" stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} />
                            <YAxis stroke="#9CA3AF" fontSize={12} tickLine={false} axisLine={false} />
                            <Tooltip content={<ThemedTooltip />} />
                            <Legend />
                            <Bar dataKey="intrusion" name="Intrusion" fill="#EF4444" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="loitering" name="Loitering" fill="#F59E0B" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};

export default RiskAnalyticsPage;