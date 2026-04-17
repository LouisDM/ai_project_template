# CLAUDE.md — AI 项目模板使用指南

**你现在打开的是一个 AI 友好的项目底座模板。** 用户会基于它提需求，你的任务是引导 **从需求 → 设计 → 开发 → 部署** 的完整流程。

## 该模板是什么

一个已经配好 AI 协作基础设施的全栈项目起点：
- **后端**：FastAPI + SQLAlchemy async + PostgreSQL + JWT 认证 + Anthropic Claude SDK 封装
- **前端**：React 19 + TypeScript + Vite + Ant Design + axios + React Router
- **部署**：Docker Compose + 直连 SSH 一键部署到 EC2
- **工作流**：`/deploy`、`/commit` 等 Claude Code 技能开箱即用

## 接到新项目时的第一步

**1. 两种部署路径，先选一个**

- **路径 A — 共享 demo 槽位（推荐做演示/验证用）**：不用改任何部署配置，直接 `python deploy.py` 上线到 https://demo.premom.tech/。模板默认就是这套。唯一注意：整个团队只能同时有一个 demo，新部署会覆盖旧的。
- **路径 B — 独立域名+端口（真要上生产走这条）**：需要改 `deploy.py` 顶部常量 + docker-compose 容器名/端口，再让管理员在 EC2 上加一份 nginx 配置。详见 `.claude/skills/deploy/SKILL.md`。

**2. 改项目身份（不改也能跑，改了更清楚）**

| 位置 | 改什么 |
|------|--------|
| 项目目录 | 从 `ai_project_template` 改成项目名 |
| `backend/app/main.py` | `FastAPI(title=...)` |
| `frontend/index.html` | `<title>` |
| `frontend/src/components/AppLayout.tsx` | 顶栏显示的应用名 |
| `frontend/src/pages/LoginPage.tsx` | 登录页标题 |
| `README.md` | 项目标题 |

**如果走路径 B（独立部署），额外要改**：

| 位置 | 改什么 |
|------|--------|
| `deploy.py` | `PROJECT_NAME`, `PUBLIC_DOMAIN`, `FRONTEND_PORT`, `BACKEND_PORT` |
| `docker-compose.prod.yml` | 容器名、ports、`networks.default.name` |
| `.env.docker.example` → `.env.docker.prod` | 真实数据库密码 + API Key |
| `backend/app/config.py` | `database_url` 默认库名（可选） |

**建议**：改名时 `grep -r "demo\|app_db"` 扫一遍避免漏改。

**2. 获取 SSH 部署密钥**（如需部署）

部署依赖 `ai-team-key` 私钥。`deploy.py` 按以下优先级查找：

1. `AI_TEAM_SSH_KEY` 环境变量
2. **项目内 `./ssh/ai-team-key`（推荐）** — 已在 `.gitignore` 忽略
3. `D:\ssh\ai-team-key`（旧位置）

如果本地没有，提醒用户向团队管理员索取，放到 `<项目>/ssh/ai-team-key`。

**3. 初始化本地环境**

```bash
# 后端
cd backend && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt
# 前端
cd frontend && npm install
# 生产环境变量
cp .env.docker.example .env.docker.prod  # 填入真实数据库密码 / API Key
# 本地开发环境
cp .env.example .env
```

**4. 根据用户需求扩展**

模板只带了 **auth + 示例 Items CRUD**。真实业务由 Claude 根据需求增量扩展：
- 新增模型：`backend/app/models.py` + `schemas.py` + 新路由文件 + 前端页面
- 新增 AI 能力：复用 `backend/app/services/ai_client.py` 的重试/降级封装

## 技术栈约定（已验证跑通）

### 后端

- **Python 3.11**，依赖全部锁定版本（`requirements.txt`）
- **SQLAlchemy 2.0 async** — 用 `Mapped` + `mapped_column` 现代风格，配 `asyncpg` 驱动
- **迁移策略**：`entrypoint.sh` 里用 `Base.metadata.create_all` + `ALTER TABLE ... IF NOT EXISTS` 幂等 DDL。**不引入 alembic**，简单项目不值得
- **认证**：JWT Bearer + bcrypt。`get_current_member` 是标准 dependency
- **AI 集成**：见 `backend/app/services/ai_client.py` — 已封装重试、`AIServiceUnavailableError` 语义化错误
- **静态文件**：上传文件挂在 `/uploads`，通过 Docker volume 持久化

### 前端

- **React 19 + TypeScript + Vite** + **verbatimModuleSyntax** 严格 type-only import
- **Ant Design 6** — 所有组件、主题定义在 `frontend/src/theme.ts`
- **axios 客户端**：`frontend/src/api/client.ts` 已加好 token 拦截器 + 401 跳转登录
- **路由**：`react-router-dom` v7，`ProtectedRoute` 包认证保护
- **日期**：`dayjs`（不要用 `moment`）
- **图标**：`@ant-design/icons`

### 部署

- **Docker Compose 生产**：`docker-compose.prod.yml` — frontend (nginx 反代 /api → backend) + backend + postgres
- **nginx 反代**：`frontend/nginx-spa.conf` — `/api/` → backend:8000，`/uploads/` 透传，SPA fallback
- **SSH 直连**：`deploy.py` 用 `paramiko` + 私钥，打包 → SFTP → 远程 `docker compose up -d --build`

## 工作流程规范

### 典型开发循环

```
用户提需求 → 你先澄清/重述 → 用 TaskCreate 拆解 → 按步实现 → 本地 typecheck+启动 → /deploy → 验证
```

**关键检查点**：
- 后端新加模型字段时，记得更新 `entrypoint.sh` 里的 `ALTER TABLE IF NOT EXISTS` 迁移
- 前端加依赖后，务必本地 `npm run build` 而不仅 `tsc --noEmit`（Docker 构建用的是 `npm run build`）
- 部署前检查 `git status`，但**不需要**强制用户提交才能部署

### 提交和部署

- `/commit` — 自动生成 Conventional Commits + 更新 `doc/CHANGELOG.md`
- `/deploy` — 全流程部署，`--check` 仅查状态，`--rebuild` 强制重建容器

### 避免的反模式

- ❌ 不要为"将来可能用到"写抽象层 — 按当前需求最小实现
- ❌ 不要引入第二个 UI 库（已有 Antd 就够）
- ❌ 不要在后端写 Python 里的 TypeScript 注释 `/* ... */`
- ❌ 不要在没有 typecheck 通过的情况下 deploy — Dockerfile 里会失败
- ❌ 不要把 `ai-team-key` 私钥提交到 git

## 常见场景速查

| 场景 | 做什么 |
|------|--------|
| 加新表 | models.py 加类 → schemas.py 加 Out/Create → routers/xxx.py 加路由 → main.py 注册 → entrypoint.sh 迁移 |
| 加新前端页面 | pages/XxxPage.tsx → App.tsx 加 Route → AppLayout.tsx 加菜单项 |
| 本地启动 | 3 个终端：`docker compose up db`、`cd backend && uvicorn app.main:app --reload`、`cd frontend && npm run dev` |
| 线上调试 | `ssh -i D:\ssh\ai-team-key ec2-user@<host>`，然后 `sudo docker logs -f <container>` |
| 修改表结构 | 优先写 `ALTER TABLE IF NOT EXISTS` 加到 entrypoint.sh；破坏性变更给清楚的回滚说明 |

## 核心文件索引

- `CLAUDE.md`（本文件）
- `README.md` — 人类可读的项目说明
- `deploy.py` — 部署入口（有详细注释）
- `backend/app/main.py` — FastAPI 主入口
- `backend/app/services/ai_client.py` — Claude SDK 封装的示范
- `frontend/src/App.tsx` — 路由总表
- `frontend/src/api/client.ts` — axios 配置
- `.claude/skills/` — Claude Code 技能目录

当你不确定某个模式该怎么写，**先读这些文件**，保持风格一致。
