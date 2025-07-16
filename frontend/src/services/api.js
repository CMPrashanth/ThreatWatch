import axios from 'axios';

const API_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

const handleApiError = (error) => {
    if (error.response) {
        const data = error.response.data;
        if (data && data.detail) {
            return data.detail;
        }
        return `Error: ${error.response.status} - ${error.response.statusText}`;
    } else if (error.request) {
        return 'Network Error: The server could not be reached. Please check your connection.';
    }
    return error.message;
};

const createApiCall = (apiCall) => async (...args) => {
    try {
        return await apiCall(...args);
    } catch (error) {
        throw new Error(handleApiError(error));
    }
};

export const register = createApiCall(async (userData) => {
    const response = await apiClient.post('/api/auth/register', userData);
    return response.data;
});

export const login = createApiCall(async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    const response = await apiClient.post('/api/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
});

export const getCurrentUser = createApiCall(async () => {
    const response = await apiClient.get('/api/users/me');
    return response.data;
});

export const updateCurrentUser = createApiCall(async (userData) => {
    const response = await apiClient.patch('/api/users/me', userData);
    return response.data;
});

export const generateTelegramLink = createApiCall(async () => {
    const response = await apiClient.post('/api/users/me/generate-telegram-link');
    return response.data;
});

export const getCameras = createApiCall(async () => {
    const response = await apiClient.get('/api/cameras');
    return response.data;
});

export const createCameraFromUrl = createApiCall(async (cameraData) => {
    const response = await apiClient.post('/api/cameras/url', cameraData);
    return response.data;
});

export const uploadCamera = createApiCall(async (name, file) => {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);
    const response = await apiClient.post('/api/cameras/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
});

export const deleteCamera = createApiCall(async (cameraId) => {
    const response = await apiClient.delete(`/api/cameras/${cameraId}`);
    return response.data;
});

export const updateCameraSettings = createApiCall(async (cameraId, settingsData) => {
    const response = await apiClient.put(`/api/cameras/${cameraId}/settings`, settingsData);
    return response.data;
});

export const updateCameraZones = createApiCall(async (cameraId, zonesData) => {
    const response = await apiClient.put(`/api/cameras/${cameraId}/zones`, zonesData);
    return response.data;
});

export const getCameraSnapshot = createApiCall(async (cameraId) => {
    const response = await apiClient.get(`/api/cameras/${cameraId}/snapshot`, { responseType: 'blob' });
    return response.data;
});

export const getIncidents = createApiCall(async (cameraId) => {
    const response = await apiClient.get(`/api/incidents/${cameraId}`);
    return response.data;
});

export const resolveIncident = createApiCall(async (incidentId) => {
    const response = await apiClient.patch(`/api/incidents/${incidentId}/resolve`);
    return response.data;
});

export const getSnapshotsByIncident = createApiCall(async (incidentId) => {
    const response = await apiClient.get(`/api/incidents/${incidentId}/snapshots`);
    return response.data;
});

export const exportIncidents = createApiCall(async (params) => {
    const response = await apiClient.get('/api/export/incidents', { params, responseType: 'blob' });
    return response.data;
});

export const getAllUsers = createApiCall(async () => {
    const response = await apiClient.get('/api/admin/users');
    return response.data;
});

export const promoteUser = createApiCall(async (userId) => {
    const response = await apiClient.post(`/api/admin/users/${userId}/promote`);
    return response.data;
});

export const getStats = createApiCall(async (cameraId) => {
    const response = await apiClient.get(`/api/stats/${cameraId}`);
    return response.data;
});

// --- Analysis Control Endpoints ---

export const startAnalysis = createApiCall(async (cameraId) => {
    const response = await apiClient.post(`/api/cameras/${cameraId}/start`);
    return response.data;
});

export const stopAnalysis = createApiCall(async (cameraId) => {
    const response = await apiClient.post(`/api/cameras/${cameraId}/stop`);
    return response.data;
});

export const pauseAnalysis = createApiCall(async (cameraId) => {
    const response = await apiClient.post(`/api/cameras/${cameraId}/pause`);
    return response.data;
});

export const playAnalysis = createApiCall(async (cameraId) => {
    const response = await apiClient.post(`/api/cameras/${cameraId}/play`);
    return response.data;
});

export const getCamerasStatus = createApiCall(async () => {
    const response = await apiClient.get('/api/cameras/status');
    return response.data;
});

export const submitComplaint = createApiCall(async (formData) => {
    const response = await apiClient.post('/api/complaint', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
});

export const getSnapshotFromUrl = createApiCall(async (imageUrl) => {
    const response = await apiClient.get('/api/public/snapshot-proxy', {
        params: { url: imageUrl },
        responseType: 'blob' // Important: expect an image blob back
    });
    return response.data;
});

export const getAnalyticsData = createApiCall(async () => {
    const response = await apiClient.get('/api/analytics/summary');
    return response.data;
});

export const getAlerts = createApiCall(async () => {
    const response = await apiClient.get('/api/alerts');
    return response.data;
});