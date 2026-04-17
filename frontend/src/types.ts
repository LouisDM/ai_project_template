export interface Member {
  id: number;
  username: string;
  name: string;
  is_admin: boolean;
}

export interface Item {
  id: number;
  title: string;
  description: string;
  created_by: number;
  created_at: string;
  updated_at: string;
}
