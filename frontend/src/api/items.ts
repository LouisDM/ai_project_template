import client from './client';
import type { Item } from '../types';

export async function listItems(): Promise<Item[]> {
  const res = await client.get<Item[]>('/items/');
  return res.data;
}

export async function createItem(data: { title: string; description?: string }): Promise<Item> {
  const res = await client.post<Item>('/items/', data);
  return res.data;
}

export async function updateItem(id: number, data: { title?: string; description?: string }): Promise<Item> {
  const res = await client.patch<Item>(`/items/${id}`, data);
  return res.data;
}

export async function deleteItem(id: number): Promise<void> {
  await client.delete(`/items/${id}`);
}
