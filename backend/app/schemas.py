from datetime import datetime
from pydantic import BaseModel


# ── Auth ──────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class MemberOut(BaseModel):
    id: int
    username: str
    name: str
    is_admin: bool = False
    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    member: MemberOut


# ── Item (example CRUD) ──────────────────────────────────
class ItemCreate(BaseModel):
    title: str
    description: str = ""


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class ItemOut(BaseModel):
    id: int
    title: str
    description: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Task ──────────────────────────────────────────────────
class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    due_date: datetime | None
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Guestbook ──────────────────────────────────────────────
class GuestbookCreate(BaseModel):
    name: str
    content: str


class GuestbookOut(BaseModel):
    id: int
    name: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}
