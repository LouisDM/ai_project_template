from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Member
from app.schemas import LoginRequest, LoginResponse, MemberOut
from app.services.auth import create_token, get_current_member, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Member).where(Member.username == req.username))
    member = result.scalar_one_or_none()
    if not member or not verify_password(req.password, member.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return LoginResponse(access_token=create_token(member.id), member=MemberOut.model_validate(member))


@router.get("/me", response_model=MemberOut)
async def me(current: Member = Depends(get_current_member)):
    return current
