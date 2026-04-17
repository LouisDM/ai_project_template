#!/bin/bash
set -e

echo "Initializing database tables..."
python -c "
import asyncio
from app.database import engine, Base
from app.models import *

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # ─────────────────────────────────────────────────────────────
        # 增量迁移区域：加字段时在这里加 ALTER TABLE ... IF NOT EXISTS
        # 示例：
        # await conn.execute(__import__('sqlalchemy').text('''
        #     DO \$\$ BEGIN
        #         ALTER TABLE members ADD COLUMN IF NOT EXISTS phone TEXT;
        #     EXCEPTION WHEN duplicate_column THEN NULL;
        #     END \$\$;
        # '''))
        # ─────────────────────────────────────────────────────────────
    print('Database tables ready.')

asyncio.run(init())
"

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
