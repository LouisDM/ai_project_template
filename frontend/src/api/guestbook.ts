import client from './client';
import type { Guestbook } from '../types';

export async function listGuestbooks(): Promise<Guestbook[]> {
  const res = await client.get<Guestbook[]>('/guestbook/');
  return res.data;
}

export async function createGuestbook(data: { name: string; content: string }): Promise<Guestbook> {
  const res = await client.post<Guestbook>('/guestbook/', data);
  return res.data;
}

export async function deleteGuestbook(id: number): Promise<void> {
  await client.delete(`/guestbook/${id}`);
}
