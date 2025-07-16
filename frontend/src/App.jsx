import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { jwtDecode } from 'jwt-decode';

import { AuthContext } from './context/AuthContext.jsx';

// Import Pages
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import IncidentsPage from './pages/IncidentsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import AlertsPage from './pages/AlertsPage.jsx';
import RiskAnalyticsPage from './pages/RiskAnalyticsPage.jsx'; 
import ComplaintPage from './pages/ComplaintPage.jsx';
import Sidebar from './components/Sidebar.jsx';
import { Toaster } from 'sonner';

const App = () => {
  const [token, setToken] = useState(localStorage.getItem('authToken'));
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (token) {
      try {
        const decodedUser = jwtDecode(token);
        setUser(decodedUser);
      } catch (error) {
        console.error("Invalid token:", error);
        localStorage.removeItem('authToken');
        setToken(null);
        setUser(null);
      }
    } else {
      setUser(null);
    }
  }, [token]);

  const setAuthToken = (newToken) => {
    if (newToken) {
      localStorage.setItem('authToken', newToken);
    } else {
      localStorage.removeItem('authToken');
    }
    setToken(newToken);
  };

  const authContextValue = {
    token,
    setAuthToken,
    user,
  };

  return (
    <AuthContext.Provider value={authContextValue}>
      <Router>
        <div className="bg-gray-900 text-white min-h-screen font-sans flex">
          <Toaster position="top-right" richColors theme="dark" />
          
          {token && <Sidebar />}
          
          <main className="flex-1">
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
              <Route path="/incidents" element={<ProtectedRoute><IncidentsPage /></ProtectedRoute>} />
              <Route path="/alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />
              <Route path="/analytics" element={<ProtectedRoute><RiskAnalyticsPage /></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
              <Route path="/complaint" element={<ProtectedRoute><ComplaintPage /></ProtectedRoute>} /> {/* Add new route */}
              <Route path="/admin" element={<AdminRoute><AdminPage /></AdminRoute>} />
              <Route path="*" element={<Navigate to={token ? "/dashboard" : "/login"} />} />
            </Routes>
          </main>
        </div>
      </Router>
    </AuthContext.Provider>
  );
};

const ProtectedRoute = ({ children }) => {
  const { token } = React.useContext(AuthContext);
  if (!token) {
    return <Navigate to="/login" />;
  }
  return children;
};

const AdminRoute = ({ children }) => {
    const { token, user } = React.useContext(AuthContext);
    if (!token) {
        return <Navigate to="/login" />;
    }
    if (user && user.role !== 'admin') {
        return <Navigate to="/dashboard" />;
    }
    return children;
};

export default App;
