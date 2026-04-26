import client from './client';
import type { Guestbook } from '../types';

const adminClient = client;

adminClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

adminClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || '';
      if (!url.includes('/admin/login')) {
        localStorage.removeItem('admin_token');
        window.location.href = '/admin/login';
      }
    }
    return Promise.reject(err);
  },
);

export async function adminLogin(username: string, password: string): Promise<{ access_token: string }> {
  const res = await adminClient.post<{ access_token: string }>('/admin/login', { username, password });
  return res.data;
}

export async function adminListGuestbooks(): Promise<Guestbook[]> {
  const res = await adminClient.get<Guestbook[]>('/admin/guestbook');
  return res.data;
}

export async function adminDeleteGuestbook(id: number): Promise<void> {
  await adminClient.delete(`/admin/guestbook/${id}`);
}
