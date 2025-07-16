import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { getCurrentUser } from '../services/api.js';
import { LayoutDashboard, AlertTriangle, Settings, LogOut, ShieldCheck, UserCircle, Shield, UserCog, Megaphone, PieChart, Siren } from 'lucide-react';
import { toast } from 'sonner';

const Sidebar = () => {
  const { setAuthToken, user: authUser } = useAuth();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const userData = await getCurrentUser();
        setUser(userData);
      } catch (error) {
        toast.error('Session expired. Please log in again.');
        handleLogout();
      }
    };
    fetchUser();
  }, []);

  const handleLogout = () => {
    setAuthToken(null);
    navigate('/login');
    toast.info('You have been logged out.');
  };

  const navItems = [
    { to: '/dashboard', icon: <LayoutDashboard size={22} />, label: 'Dashboard' },
    { to: '/incidents', icon: <AlertTriangle size={22} />, label: 'Incidents' },
    { to: '/alerts', icon: <Siren size={22} />, label: 'Alerts' },
    { to: '/analytics', icon: <PieChart size={22} />, label: 'Analytics' },
    { to: '/settings', icon: <Settings size={22} />, label: 'Settings' },
    { to: '/complaint', icon: <Megaphone size={22} />, label: 'File Complaint' },
  ];
  
  const adminNavItem = { to: '/admin', icon: <UserCog size={22} />, label: 'Admin' };

  const baseLinkClass = "flex items-center p-3 my-1 rounded-lg transition-colors duration-200";
  const inactiveLinkClass = "text-gray-400 hover:bg-gray-800 hover:text-white";
  const activeLinkClass = "bg-indigo-600 text-white font-semibold";

  return (
    // The h-screen class ensures the sidebar takes the full viewport height.
    // The 'sticky' and 'top-0' classes make it stay in place during scroll.
    <div className="bg-gray-950 w-64 h-screen flex flex-col p-4 border-r border-gray-800 sticky top-0">
      <div className="flex items-center space-x-3 p-2 mb-4">
        <ShieldCheck className="h-10 w-10 text-indigo-500" />
        <span className="text-xl font-bold text-white">ThreatWatch</span>
      </div>

      {/* The flex-1 class on the nav element makes it expand to fill available space, pushing the user profile to the bottom */}
      <nav className="flex-1 space-y-2 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `${baseLinkClass} ${isActive ? activeLinkClass : inactiveLinkClass}`}
          >
            {item.icon}
            <span className="ml-4">{item.label}</span>
          </NavLink>
        ))}
        
        {authUser && authUser.role === 'admin' && (
            <NavLink
                to={adminNavItem.to}
                className={({ isActive }) => `${baseLinkClass} ${isActive ? activeLinkClass : inactiveLinkClass}`}
            >
                {adminNavItem.icon}
                <span className="ml-4">{adminNavItem.label}</span>
            </NavLink>
        )}
      </nav>

      {/* This section will now be at the bottom of the sidebar */}
      <div className="border-t border-gray-800 pt-4 mt-auto">
        <div className="flex items-center p-2 rounded-lg">
          <div className="relative">
            <UserCircle size={36} className="text-gray-500" />
            {authUser && authUser.role === 'admin' && (
                <Shield size={16} className="absolute bottom-0 right-0 text-yellow-400 bg-gray-950 rounded-full p-0.5" />
            )}
          </div>
          <div className="ml-3">
            <p className="text-sm font-semibold text-white">{user ? user.username : 'Loading...'}</p>
            <p className="text-xs text-gray-400">{user ? user.email : '...'}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className={`${baseLinkClass} ${inactiveLinkClass} w-full mt-2`}
        >
          <LogOut size={22} />
          <span className="ml-4">Logout</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
