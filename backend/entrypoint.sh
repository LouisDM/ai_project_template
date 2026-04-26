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
        # 增量迁移：tasks 表
        await conn.execute(__import__('sqlalchemy').text('''
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT DEFAULT '',
                status VARCHAR(20) DEFAULT 'todo',
                priority VARCHAR(20) DEFAULT 'medium',
                due_date TIMESTAMP NULL,
                created_by INTEGER REFERENCES members(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        '''))
        # ─────────────────────────────────────────────────────────────
        # 增量迁移：guestbook 表
        await conn.execute(__import__('sqlalchemy').text('''
            CREATE TABLE IF NOT EXISTS guestbook (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                is_deleted BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        '''))
        # ─────────────────────────────────────────────────────────────
        # Seed default member so /login works out of the box
        from passlib.context import CryptContext
        _pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')
        _hash = _pwd.hash('admin123')
        await conn.execute(__import__('sqlalchemy').text(f'''
            INSERT INTO members (id, username, password_hash, name, is_admin)
            VALUES (1, 'admin', '{_hash}', '管理员', true)
            ON CONFLICT (id) DO NOTHING;
        '''))
    print('Database tables ready.')

asyncio.run(init())
"

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
