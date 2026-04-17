"""Example CRUD router — replace / extend for your real domain."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Item, Member
from app.schemas import ItemCreate, ItemOut, ItemUpdate
from app.services.auth import get_current_member

router = APIRouter(prefix="/api/items", tags=["items"])


@router.get("/", response_model=list[ItemOut])
async def list_items(
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(get_current_member),
):
    result = await db.execute(select(Item).order_by(Item.id.desc()))
    return result.scalars().all()


@router.post("/", response_model=ItemOut, status_code=201)
async def create_item(
    req: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current: Member = Depends(get_current_member),
):
    item = Item(title=req.title, description=req.description, created_by=current.id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: int,
    req: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(get_current_member),
):
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if req.title is not None:
        item.title = req.title
    if req.description is not None:
        item.description = req.description
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _: Member = Depends(get_current_member),
):
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
