---
name: multica-flow
description: Multica 平台需求到部署全流程 — 从 Issue 读取需求，开发、部署、测试，回写部署地址到 Issue 评论。由 Multica 代理触发。
user_invocable: false
---

# multica-flow — 需求到部署全流程

## 铁律（执行前必读，逐条自检）

1. **禁止创建新项目** — 所有代码增量添加到 `ai_project_template`
2. **不写 Issue 评论 = 任务失败** — 每个 Sprint 完成后必须评论
3. **不提交不能部署** — `git diff HEAD~1 --quiet` 通过才能继续
4. **必须获取/释放部署锁** — 无论成功失败，锁必须释放
5. **本地验证失败不能部署** — `tsc --noEmit`、`vite build`、`python import` 全绿
6. **禁止改端口/域名配置** — 不改 `deploy.py`、`docker-compose.prod.yml`
7. **模型和路由只追加不删除** — 新模型加 `models.py` 末尾，新路由加 `routers/` 目录
8. **AI 调用必须降级** — LLM 失败返回空值，不抛异常阻断流程
9. **空数据必须保护** — 数组/对象操作前检查 null/undefined/length
10. **Contract 功能必须完整** — 筛选、排序、分页等辅助功能不能漏做
11. **部署环境变量必须通过 shell 传入** — `FRONTEND_PORT`/`PROJECT_NAME` 需用 `sudo -E docker compose` 显式传递，不能仅写入 `.env.docker`
12. **Admin 认证 API 必须独立实例** — admin 登录相关请求使用独立 `axios.create()`，避免通用 client 的 401 拦截器吞掉登录错误提示
13. **登录错误必须显示提示** — 失败时调用 `message.error('账号或密码错误')` 或等效方法，禁止静默失败
14. **项目身份必须随 Issue 更新** — `main.py` 的 `FastAPI(title=...)`、`index.html` 的 `<title>`、`AppLayout.tsx` 的应用名、`LoginPage.tsx` 的标题，都必须根据 Issue 标题更新，不能保留 "AI Project Template"
15. **entrypoint.sh 必须包含管理员初始化** — 如果项目有 admin 功能，在 `entrypoint.sh` 的 `init()` 中通过 `INSERT INTO ... ON CONFLICT DO NOTHING` 创建默认管理员账号（从环境变量读取），确保首次启动即可登录
16. **统计/图表后端 API 必须返回标准格式** — 任何涉及 KPI、图表、数据洞察的功能，后端必须提供独立 REST 接口（如 `/api/xxx/stats`），返回结构为 `{ totals: {...}, distribution: [...], trend: [...], ai_summary: "..." }`。禁止让前端直接遍历全量数据做统计计算
17. **任何失败必须写评论说明原因** — 部署失败、评估失败、测试失败，都必须用 `multica issue comment add` 写明失败原因和日志摘要。禁止静默标记 blocked 或不写评论直接退出

---

## 执行流程

### Step 1 — 读取需求

```bash
multica issue get <ISSUE_ID> --output json
multica issue status <ISSUE_ID> in_progress
```

提取 `description`，有附件则下载读取。

### Step 2 — 验证工作目录并理解现有代码

**2.1 验证工作目录（STOP 自检）**

运行以下检查确认当前目录是 `ai_project_template`：

```bash
# 必须存在的关键文件
test -f CLAUDE.md && test -f backend/app/main.py && test -f frontend/src/App.tsx && test -f deploy.py && echo "VALID" || echo "INVALID"

# 检查 deploy.py 大小（模板约 7900 bytes）
python3 -c "import os; s=os.path.getsize('deploy.py'); print('OK' if s > 5000 else f'INVALID: deploy.py={s}b')"

# 检查是否有 PostgreSQL/asyncpg（模板有，独立项目通常没有）
grep -q asyncpg backend/requirements.txt 2>/dev/null && echo "HAS_ASYNCPG" || echo "MISSING_ASYNCPG"
```

**CHECKPOINT**: 如果任一检查返回 INVALID：
- **STOP，不要继续编码**
- 使用正确的模板目录：
  ```bash
  cd /Users/louis/Downloads/配置任务/ai_project_template
  ```
- 如果目录不存在或有冲突，clone 最新代码：
  ```bash
  git clone https://github.com/LouisDM/ai_project_template.git /tmp/ai_project_template
  cd /tmp/ai_project_template
  ```

**2.2 理解现有代码**

读 `CLAUDE.md`、`backend/app/main.py`、`frontend/src/App.tsx`，制定实现方案。

**CHECKPOINT**: 方案确定后，用 `multica issue comment add` 告知用户。用户说「确认」或「直接开始」才继续。

### Step 3 — 开发实现

按增量原则修改：
- `models.py` 末尾追加新模型类
- `schemas.py` 末尾追加新 schema
- `routers/` 下新建路由文件，`main.py` 中注册
- `pages/` 下新建页面，`App.tsx` 加路由，`AppLayout.tsx` 加菜单
- `entrypoint.sh` 追加 `CREATE TABLE IF NOT EXISTS`

**前端约束**：面向最终用户设计，不出现「API」「Schema」「路由」等技术词汇。
- 表单输入必须用原生 `<input>`、`<textarea>`、`<select>`，禁止用 div/span 模拟
- 所有 `.map()`、`.filter()` 操作前检查 `Array.isArray(data) && data.length > 0`
- 图表组件数据为空时传入 `[]`，不要传 undefined
- 空状态显示 Empty 组件或提示文字，禁止页面空白或报错

**后端约束**：
- AI 调用必须 try-catch，失败返回空值/默认值：`try: label = await ai_client.classify(content); except: label = ""`
- 数据库查询返回的数据必须包含 Contract 要求的所有字段

**统计/图表功能约束**：
- 涉及数据洞察、KPI、图表的功能，后端必须提供独立聚合接口（如 `/api/xxx/stats`）
- 统计接口必须处理空数据情况：返回 0 值或空数组，不能抛异常
- 前端统计页面必须对接后端统计接口，禁止前端遍历全量数据做聚合计算
- AI 洞察摘要由后端生成后通过统计接口返回，前端只做展示

**功能完整性约束**：
- Contract 要求"筛选"→ 必须实现筛选控件；要求"分页"→ 必须实现分页组件
- 禁止只做主体功能而漏做辅助功能

### Step 4 — 本地验证（STOP 自检）

```bash
cd frontend && npx tsc --noEmit
cd frontend && npx vite build
cd backend && python -c "from app.main import app; print('OK')"
```

**CHECKPOINT**: 任意一条失败 → STOP，修到通过。

**额外自检 — 数据保存验证**：
启动后端后，用 curl 测试 API 写入和读取：
```bash
# 写入测试数据
curl -X POST http://localhost:8000/api/<路由> \
  -H "Content-Type: application/json" \
  -d '<测试数据>'
# 查询确认数据存在
curl http://localhost:8000/api/<路由>
```
**如果查不到记录 → STOP，修复保存逻辑。**

### Step 5 — 提交（STOP 自检）

```bash
git add -A
git commit -m "feat: <需求摘要>"
```

**CHECKPOINT**: 运行 `git diff HEAD~1 --quiet`。
- 无输出 = 有新提交，继续
- 有输出 = 提交失败，STOP 修错误

### Step 6 — 部署

**6.1 获取锁**

```python
import paramiko, sys
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('47.121.130.229', username='root', password='P6ZxidTmtks!qPC', timeout=10)
_, out, _ = c.exec_command('cat /root/.deploy_lock 2>/dev/null; echo "EXIT=$?"')
if 'DEPLOYING' in out.read().decode():
    print('LOCKED'); sys.exit(1)
c.exec_command('echo DEPLOYING_$(date +%s) > /root/.deploy_lock')
c.close()
```

**6.2 执行部署**

```bash
python deploy.py -y --name <项目名>
```

项目名从 Issue 标题提取，小写替换空格为连字符。

**6.3 释放锁（强制，无论成败）**

```python
import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('47.121.130.229', username='root', password='P6ZxidTmtks!qPC', timeout=10)
c.exec_command('rm -f /root/.deploy_lock')
c.close()
```

### MANDATORY STEP 7 — 写 Issue 评论（BLOCKING，不可跳过）

**这一步是 BLOCKING 的。不写评论，任务不算完成。**

```bash
multica issue status <ISSUE_ID> in_review
```

```bash
multica issue comment add <ISSUE_ID> --content "## Sprint <N> 完成 ✓

**实现内容**：
- <交付物 1>
- <交付物 2>

**部署地址**：http://<分配的域名>/
**登录**：admin / admin123

**验证结果**：
- [x] 本地 typecheck 通过
- [x] 本地 build 通过
- [x] 后端 import 正常
- [x] API 数据保存验证通过
- [x] 部署成功
- [x] 健康检查 200

请验收。"
```

**CHECKPOINT**: 评论发送后，重读 Issue 确认评论存在。如果不存在，重试 3 次，仍失败则保存到 `issue_comment.md`。

---

## 失败处理

| 场景 | 操作 |
|------|------|
| 本地验证失败 | STOP，修复错误，回到 Step 4 |
| 部署锁被占 | sleep 60 重试，最多 5 次，仍锁则评论告知用户 |
| 部署失败 | 先释放锁，再评论贴错误日志，状态设为 blocked |
| 评论发送失败 | 重试 3 次，保存到本地 `issue_comment.md` |
| 统计 API 返回异常 | 检查后端聚合查询 SQL，确保空数据返回 0 值而非抛异常 |
| Evaluator 不写评论 | Generator 收到 in_review 但无评估报告时，主动评论询问评估状态 |
| 标记 blocked 前不写评论 | 绝对禁止。任何 blocked 必须先写评论说明原因和日志 |
