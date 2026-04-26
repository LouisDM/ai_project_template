"""Guestbook router — public message board."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Guestbook
from app.schemas import GuestbookCreate, GuestbookOut

router = APIRouter(prefix="/api/guestbook", tags=["guestbook"])


@router.get("/", response_model=list[GuestbookOut])
async def list_guestbooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Guestbook)
        .where(Guestbook.is_deleted == False)
        .order_by(desc(Guestbook.created_at))
        .limit(100)
    )
    return result.scalars().all()


@router.post("/", response_model=GuestbookOut, status_code=201)
async def create_guestbook(req: GuestbookCreate, db: AsyncSession = Depends(get_db)):
    name = req.name.strip()
    content = req.content.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="姓名不能为空")
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="内容不能为空")
    if len(name) > 50:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="姓名不能超过50字")
    if len(content) > 2000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="内容不能超过2000字")

    gb = Guestbook(name=name, content=content)
    db.add(gb)
    await db.commit()
    await db.refresh(gb)
    return gb
