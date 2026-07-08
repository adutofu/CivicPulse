import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          // Note: You'll need to add a refresh endpoint to your Django API
          // For now, log user out
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } catch (err) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (username, password) =>
    apiClient.post('/auth/login/', { username, password }),
  
  signup: (username, email, password, user_type = 'citizen', agency = '') =>
    apiClient.post('/auth/signup/', { username, email, password, user_type, agency }),
  
  getProfile: () => apiClient.get('/auth/profile/'),
  
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_type');
  },
};

export const complaintAPI = {
  getAll: (params = {}) => apiClient.get('/complaints/', { params }),
  
  getOne: (id) => apiClient.get(`/complaints/${id}/`),
  
  create: (data) => apiClient.post('/complaints/', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  
  update: (id, data) => apiClient.patch(`/complaints/${id}/`, data),
  
  updateStatus: (id, data) => apiClient.post(`/complaints/${id}/update_status/`, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  
  addImage: (id, file) => {
    const formData = new FormData();
    formData.append('image', file);
    return apiClient.post(`/complaints/${id}/add_image/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const voteAPI = {
  toggle: (complaintId) =>
    apiClient.post(`/votes/toggle/${complaintId}/`),
};

export const notificationAPI = {
  getAll: (params = {}) => apiClient.get('/notifications/', { params }),
  
  getUnreadCount: () => apiClient.get('/notifications/unread_count/'),
  
  markRead: (id) => apiClient.post(`/notifications/${id}/mark_read/`),
  
  markAllRead: () => apiClient.post('/notifications/mark_all_read/'),
};

export default apiClient;
