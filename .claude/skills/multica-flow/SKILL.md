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

### Step 2 — 签出项目代码（基于 ai_project_template）

**⚠️ 关键约束：所有开发必须基于 ai_project_template，禁止创建新项目**

如果工作目录已经有 ai_project_template 代码，直接使用它。如果没有，尝试：

```bash
multica repo checkout
```

如果 checkout 失败或创建了新目录，使用本地已知的 ai_project_template：

```bash
# 使用本地已配置的模板（推荐）
cd /Users/louis/Downloads/配置任务/ai_project_template

# 或者从 git 拉取
git clone <仓库地址> . 2>/dev/null || echo "使用现有代码"
```

**禁止行为**：
- ❌ 创建新的项目目录（如 knowledge-base/、my-app/ 等）
- ❌ 初始化新的 npm/python 项目
- ❌ 修改技术栈（必须用 FastAPI + React + PostgreSQL）
- ❌ 修改 docker-compose.prod.yml 的端口映射（deploy.py 会自动分配）
- ❌ 修改 deploy.py 的常量（Agent 调用 deploy.py 时会自动分配端口和域名）
- ❌ **删除或替换现有模型（models.py）** — 新模型必须追加到现有文件末尾，保留所有已有模型类
- ❌ **修改或删除现有路由文件**（如 auth.py、items.py、tasks.py）— 新增路由文件到 routers/ 目录
- ❌ **删除或替换现有前端页面** — 新增页面文件，保留已有页面

**正确做法**：
- ✅ 在现有 backend/app/ 下**追加**新模型到 models.py 末尾，**追加**新 schema 到 schemas.py
- ✅ 在 routers/ 下**新建**路由文件（如 routers/knowledge.py），在 main.py 中注册
- ✅ 在现有 frontend/src/pages/ 下**新建**页面文件，在 App.tsx 中新增路由
- ✅ 只修改：main.py（注册新路由）、App.tsx（新增路由）、AppLayout.tsx（新增菜单）
- ✅ 复用已有的认证、数据库配置、部署流程

### Step 3 — 就位部署配置

项目目录下已有 `.env.docker.prod`（包含数据库密码等生产配置），部署脚本会自动将其复制为 `.env.docker`。

如需自定义生产配置，可直接修改项目根目录的 `.env.docker.prod`：

```bash
# 生产环境配置已在项目中，如需修改直接编辑
vim .env.docker.prod
```

同时确保 `SSH_PASSWORD` 环境变量已设置：

```bash
export SSH_PASSWORD="你的服务器密码"
```

如果 `.env.docker.prod` 不存在，**立即停止**并通过 Issue 评论告知用户：

```bash
multica issue comment add <ISSUE_ID> --content "⚠️ 部署配置缺失：找不到 .env.docker.prod，请确保项目根目录包含此文件。"
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
- 新加模型：在现有 `models.py` **文件末尾追加**新模型类，不要删除已有类；在现有 `schemas.py` **文件末尾追加**新 schema
- 新加路由：在 `routers/` 下**新建**路由文件（如 `knowledge.py`），在 `main.py` 中**追加**注册
- 新加前端页面：在 `pages/` 下**新建**页面文件，在 `App.tsx` 中**追加**路由，在 `AppLayout.tsx` 中**追加**菜单项
- 项目身份同步（新项目必须）：同步更新 `frontend/index.html` 的 `<title>`、`frontend/src/components/AppLayout.tsx` 顶栏标题、`frontend/src/pages/LoginPage.tsx` 登录页标题、`backend/app/main.py` 的 `FastAPI(title="...")`
- 数据库迁移：在 `entrypoint.sh` 中**追加** `CREATE TABLE IF NOT EXISTS` 和 `ALTER TABLE IF NOT EXISTS` 语句

**前端面向用户（非开发者）的约束**：
- 页面标题、菜单、按钮用业务语言，不要出现「API」「路由」「Schema」等技术词汇
- 登录页只显示系统名称 + 用户名密码输入框，不要显示技术栈说明或后端版本信息
- 页面上的说明文字教用户「如何操作」，不要解释「技术实现」
- 列表页、表单页、详情页面向最终用户设计，类似主流 SaaS 产品

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

**8.1 检查是否有其他任务正在部署（部署竞争锁）**

多个任务同时部署到同一台服务器会互相覆盖代码，导致部署失败或功能异常。部署前必须先检查锁：

```bash
# 方式一：检查远程锁文件
python -c "
import paramiko, sys
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('47.121.130.229', username='root', password='P6ZxidTmtks!qPC', timeout=10)
stdin, stdout, stderr = client.exec_command('cat /root/.deploy_lock 2>/dev/null; echo \"EXIT_CODE=$?\"')
out = stdout.read().decode()
client.close()
if 'DEPLOYING' in out:
    print('LOCKED')
    sys.exit(1)
else:
    print('FREE')
"
```

如果返回 `LOCKED`，说明有其他任务正在部署：
- **等待并重试**：sleep 60 秒后再次检查，最多重试 5 次
- **如果一直锁定**：在 Issue 评论告知用户有并发部署冲突，等待而非强制覆盖

**获取到锁之后才继续**：
```bash
python -c "
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('47.121.130.229', username='root', password='P6ZxidTmtks!qPC', timeout=10)
client.exec_command('echo DEPLOYING_\$(date +%s) > /root/.deploy_lock')
client.close()
"
```

**8.2 执行部署**

**必须指定项目名**，每个项目部署到独立目录，避免代码互相覆盖：

```bash
python deploy.py -y --name <项目名>
```

项目名规则：
- 从 Issue 标题提取关键词，转为小写、替换空格为连字符
- 例如：Issue "员工通讯录管理系统" → `--name addressbook`
- 例如：Issue "会议室预约系统" → `--name meeting-room`

deploy.py 会自动：
1. 扫描服务器端口，从 22222-22333 范围自动分配一个未使用的端口
2. 从项目名自动生成二级域名（如 `addressbook.demo.intelliastra.com`）
3. 在服务器上自动生成 nginx 反向代理配置
4. 打包 → SSH 传输到 EC2 → docker compose up --build → 健康检查
5. 部署完成后返回分配的域名和端口

**部署目录**：`/root/<项目名>/`（每个项目独立，互不干扰）

**8.3 释放锁**

```bash
python -c "
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('47.121.130.229', username='root', password='P6ZxidTmtks!qPC', timeout=10)
client.exec_command('rm -f /root/.deploy_lock')
client.close()
"
```

部署失败时，**先释放锁**，再把错误日志贴到 Issue 评论，更新状态为 blocked：
```bash
multica issue comment add <ISSUE_ID> --content "⚠️ 部署失败：\n\`\`\`\n<错误信息>\n\`\`\`"
multica issue status <ISSUE_ID> blocked
```

### Step 9 — 验证上线

```bash
curl -sf --max-time 10 -o /dev/null -w "%{http_code}" http://<分配的域名>/
curl -sf --max-time 10 http://<分配的域名>/health
```

### Step 10 — 回写 Issue

验证通过后，更新 Issue 状态并发布完成评论：

```bash
multica issue status <ISSUE_ID> in_review

multica issue comment add <ISSUE_ID> --content "完成上线 ✓

**域名入口**：http://<分配的域名>/
**登录**：admin / admin123（或 seed 中设置的密码）

**功能说明**（面向用户）：
- [功能1]：如何操作、能达到什么效果
- [功能2]：如何操作、能达到什么效果
- ...

**使用指引**：
1. 打开地址，用 admin 账号登录
2. 在左侧菜单选择 [功能模块名称]
3. [具体操作步骤]

请验收，有问题直接在这里留言。"
```

**回写约束**：
- 面向最终用户写功能说明，不要罗列技术文件或 API 路由
- 提供清晰的使用步骤，让用户知道「点哪里、做什么"
- 密码变更时必须在评论中说明

---

## 重要约束

1. **必须在 ai_project_template 上开发** — 禁止创建新项目或独立应用，所有代码增量添加到现有项目中
2. **禁止修改端口和部署配置** — 不要改 deploy.py 的 PROJECT_NAME / PUBLIC_DOMAIN / FRONTEND_PORT(7005) / BACKEND_PORT(8006)，不要改 docker-compose.prod.yml 的端口映射
3. **Step 3 文件缺失 → 立即 blocked**，不要尝试绕过
4. **Step 6 验证失败 → 必须修到绿**，不能带错误部署
5. **部署失败 → blocked + 贴错误信息**，不要静默失败
6. **所有进展都通过 Issue 评论告知用户**，不要让用户盲等
