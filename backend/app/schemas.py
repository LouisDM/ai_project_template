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
