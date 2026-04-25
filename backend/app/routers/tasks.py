"""Task router — Todo App CRUD."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database import AsyncSession, get_db
from app.models import Task, Member
from app.schemas import TaskCreate, TaskUpdate, TaskOut
from app.routers.auth import get_current_member

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    status: str | None = Query(None, description="Filter by status: todo or done"),
    session: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    query = select(Task).where(Task.created_by == current_member.id)
    if status:
        query = query.where(Task.status == status)
    query = query.order_by(desc(Task.created_at))
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/", response_model=TaskOut, status_code=201)
async def create_task(
    data: TaskCreate,
    session: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    task = Task(
        title=data.title,
        description=data.description,
        priority=data.priority,
        due_date=data.due_date,
        created_by=current_member.id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    result = await session.execute(
        select(Task).where(Task.id == task_id, Task.created_by == current_member.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    task.updated_at = datetime.now()

    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
    current_member: Member = Depends(get_current_member),
):
    result = await session.execute(
        select(Task).where(Task.id == task_id, Task.created_by == current_member.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await session.delete(task)
    await session.commit()
