"""Admin router — guestbook management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Guestbook
from app.schemas import GuestbookOut
from app.config import settings
from app.services.auth import create_token, get_current_member
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBearer()


class AdminLoginRequest:
    pass


@router.post("/login")
async def admin_login(req: dict):
    username = req.get("username", "")
    password = req.get("password", "")
    if username != settings.admin_username or password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    token = create_token(-1)  # -1 表示管理员
    return {"access_token": token}


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> bool:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        member_id = int(payload["sub"])
        if member_id != -1:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return True


@router.get("/guestbook", response_model=list[GuestbookOut])
async def admin_list_guestbooks(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(get_current_admin),
):
    result = await db.execute(
        select(Guestbook)
        .where(Guestbook.is_deleted == False)
        .order_by(desc(Guestbook.created_at))
        .limit(200)
    )
    return result.scalars().all()


@router.delete("/guestbook/{guestbook_id}", status_code=204)
async def admin_delete_guestbook(
    guestbook_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(get_current_admin),
):
    gb = await db.get(Guestbook, guestbook_id)
    if not gb:
        raise HTTPException(status_code=404, detail="留言不存在")
    gb.is_deleted = True
    await db.commit()
