import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const RAW_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_BASE_URL = RAW_URL.replace(/\/+$/, '');

export function buildApiUrl(path) {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refreshToken = useAuthStore.getState().refreshToken;
        const { data } = await axios.post(
          buildApiUrl('/auth/refresh'),
          { refresh_token: refreshToken }
        );
        useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export default api;
