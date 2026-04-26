from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="留言板", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


from app.routers import auth, items, tasks, guestbook, admin
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(tasks.router)
app.include_router(guestbook.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
