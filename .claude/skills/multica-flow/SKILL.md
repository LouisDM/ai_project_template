---
name: multica-flow
description: Multica 平台专用的需求到部署全流程 — 从 Multica Issue 读取需求，完成开发、部署、测试，将上线地址回写到 Issue 评论。由 Multica 代理触发，非 CLI 用户直接调用。
user_invocable: false
---

# multica-flow — Multica 需求到部署全流程

**触发方式**：Multica Issue 分配给本 Agent 时自动执行。用户在 Issue 描述里写需求，Agent 从这里读取，完成从开发到上线的完整流程。

---

## 执行流程

### Step 1 — 读取需求

```bash
multica issue get <ISSUE_ID> --output json
```

从 Issue 的 `description` 字段提取需求内容。如果有附件（PRD 文档），用 `multica attachment download <id>` 下载并读取。

将 Issue 状态更新为进行中：
```bash
multica issue status <ISSUE_ID> in_progress
```

### Step 2 — 签出项目代码

```bash
multica repo checkout <AI_PROJECT_TEMPLATE_REPO_URL>
```

签出完成后，进入项目目录（通常是仓库名对应的子目录）。后续所有操作都在这个目录内执行。

### Step 3 — 就位部署配置

项目需要以下文件才能部署，它不在 git 里，从固定路径复制：

```bash
# 生产环境配置（包含数据库密码等）
cp /Users/admin/Documents/ai_project/ai-team-file/.env.docker.prod .env.docker.prod
```

同时确保 `SSH_PASSWORD` 环境变量已设置：

```bash
export SSH_PASSWORD="你的服务器密码"
```

如果 `.env.docker.prod` 不存在，**立即停止**并通过 Issue 评论告知用户：

```bash
multica issue comment add <ISSUE_ID> --content "⚠️ 部署配置缺失：找不到 .env.docker.prod，请联系 AI 部门确认 /Users/admin/Documents/ai_project/ai-team-file/ 目录内容完整。"
multica issue status <ISSUE_ID> blocked
```

### Step 4 — 理解需求，制定方案

基于 Step 1 读取的需求：
1. 读 `CLAUDE.md` 了解技术栈
2. 读 `backend/app/main.py`、`frontend/src/App.tsx` 了解现有结构
3. 制定实现方案：要改哪些文件、加哪些模型/接口/页面

通过 Issue 评论输出方案摘要，等待用户确认：

```bash
multica issue comment add <ISSUE_ID> --content "我的实现方案：

1. [具体任务1]
2. [具体任务2]
...

回复「确认」开始开发，或告诉我需要调整的地方。"
```

**等待用户回复**（通过下一次 comment-triggered task 触发继续）。

> 如果用户在 Issue 描述里已经明确说了「直接开始」或「不需要确认」，跳过这一步直接进 Step 5。

### Step 5 — 开发实现

按方案逐步实现，遵守 `CLAUDE.md` 里的技术栈约定：
- 新加模型：`models.py` + `schemas.py` + `routers/` + `main.py 注册` + `entrypoint.sh 迁移`
- 新加前端页面：`pages/` + `App.tsx 路由` + `AppLayout.tsx 菜单`

### Step 6 — 本地验证

```bash
cd frontend && npx tsc --noEmit
cd frontend && npx vite build
cd backend && python -c "from app.main import app; print('OK')"
```

任何一步失败必须修到通过，不带错误继续。

### Step 7 — 提交

```bash
git add -A
git commit -m "feat: <需求一句话摘要>"
```

### Step 8 — 部署

```bash
python deploy.py -y
```

deploy.py 会自动：打包 → SSH 传输到 EC2 → docker compose up --build → 健康检查。

部署失败时，把错误日志贴到 Issue 评论，更新状态为 blocked：
```bash
multica issue comment add <ISSUE_ID> --content "⚠️ 部署失败：\n\`\`\`\n<错误信息>\n\`\`\`"
multica issue status <ISSUE_ID> blocked
```

### Step 9 — 验证上线

```bash
curl -sf --max-time 10 https://demo.premom.tech/health
curl -sf --max-time 10 -o /dev/null -w "%{http_code}" https://demo.premom.tech/
```

### Step 10 — 回写 Issue

验证通过后，更新 Issue 状态并发布完成评论：

```bash
multica issue status <ISSUE_ID> in_review

multica issue comment add <ISSUE_ID> --content "完成上线 ✓

**地址**：https://demo.premom.tech/
**功能**：[简述实现了什么]
**改动**：[后端 X 文件，前端 Y 文件]

请验收，有问题直接在这里留言。"
```

---

## 重要约束

1. **Step 3 文件缺失 → 立即 blocked**，不要尝试绕过
2. **Step 6 验证失败 → 必须修到绿**，不能带错误部署
3. **部署失败 → blocked + 贴错误信息**，不要静默失败
4. **所有进展都通过 Issue 评论告知用户**，不要让用户盲等
5. **不要修改 deploy.py 的 PROJECT_NAME / PUBLIC_DOMAIN / 端口**，固定使用 demo 槽位
