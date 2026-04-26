import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || '';
      // 排除登录请求本身，避免登录失败时刷新页面导致错误提示无法显示
      if (!url.includes('/auth/login')) {
        localStorage.removeItem('token');
        localStorage.removeItem('member');
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  },
);

export default client;
