# AI Project Template

AI 友好的全栈项目模板 — 拿到模板改个名字，直接在 Claude Code 里提需求即可开始开发。

## 技术栈

- **后端**：FastAPI · SQLAlchemy 2.0 async · PostgreSQL · JWT · Anthropic Claude SDK
- **前端**：React 19 · TypeScript · Vite · Ant Design 6 · React Router · axios
- **部署**：Docker Compose · SSH 直连 EC2（`paramiko`）

## 快速开始

### 1. 克隆并重命名

```bash
# 复制整个模板目录并改名为你的项目名
cp -r D:\ai_project_template D:\Projects\your_project_name
cd D:\Projects\your_project_name
```

根据 `CLAUDE.md` 里的「确认项目命名」清单改一遍各文件。

### 2. 获取部署密钥（如需上线）

向团队管理员索取 `ai-team-key`，放到项目内 `./ssh/ai-team-key`（`.gitignore` 已忽略）。

查找优先级：`AI_TEAM_SSH_KEY` 环境变量 → `./ssh/ai-team-key` → `D:\ssh\ai-team-key`。

### 3. 配置环境变量

```bash
cp .env.example .env                    # 本地开发
cp .env.docker.example .env.docker.prod # 生产（填入真实密钥）
```

### 4. 本地跑起来

```bash
# 启动数据库（Docker）
docker compose up db -d

# 后端
cd backend
python -m venv .venv
.venv/Scripts/activate     # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端（新终端）
cd frontend
npm install
npm run dev                # http://localhost:5173
```

### 5. 部署到生产

```bash
python deploy.py            # 完整部署
python deploy.py --check-only   # 只检查服务器状态
```

## 常用 Claude Code 技能

- `/deploy` — 一键部署（详见 `.claude/skills/deploy/SKILL.md`）
- `/commit` — 智能提交 + 更新 CHANGELOG（详见 `.claude/skills/commit/SKILL.md`）

## 项目约定

**代码风格、测试策略、架构决策全部写在 `CLAUDE.md` 里。** 开新会话时 Claude 会自动加载它。

## 默认 demo 部署槽位

模板开箱即用部署到共享测试环境：

| 项目 | 值 |
|------|-----|
| 对外域名 | **https://demo.premom.tech/**（HTTPS 泛域名证书） |
| 前端直连 | http://cms.premom.tech:9700 |
| 后端直连 | http://cms.premom.tech:8006 |

> demo 槽位整团队共用，新部署会覆盖旧的。要独立部署请见 `.claude/skills/deploy/SKILL.md` 的「独立部署配置」章节。

## 默认端口

| 服务 | 本地开发 | demo 生产 |
|------|---------|----------|
| 前端 | 5173 | 9700 |
| 后端 | 8000 | 8006 |
| PostgreSQL | 5433 | 内部网络 |
