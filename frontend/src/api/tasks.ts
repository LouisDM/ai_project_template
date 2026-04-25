import client from './client';

export interface Task {
  id: number;
  title: string;
  description: string;
  status: 'todo' | 'done';
  priority: 'low' | 'medium' | 'high';
  due_date: string | null;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
  priority?: string;
  due_date?: string | null;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  status?: string;
  priority?: string;
  due_date?: string | null;
}

export function listTasks(status?: string) {
  return client.get<Task[]>('/tasks/', { params: status ? { status } : undefined });
}

export function createTask(data: TaskCreate) {
  return client.post<Task>('/tasks/', data);
}

export function updateTask(id: number, data: TaskUpdate) {
  return client.patch<Task>(`/tasks/${id}`, data);
}

export function deleteTask(id: number) {
  return client.delete(`/tasks/${id}`);
}
