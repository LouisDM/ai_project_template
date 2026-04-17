import client from './client';
import type { Member } from '../types';

export interface LoginResponse {
  access_token: string;
  member: Member;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await client.post<LoginResponse>('/auth/login', { username, password });
  return res.data;
}

export async function getMe(): Promise<Member> {
  const res = await client.get<Member>('/auth/me');
  return res.data;
}
