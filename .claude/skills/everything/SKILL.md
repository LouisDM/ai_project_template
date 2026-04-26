---
name: everything
description: 零技术门槛全流程向导 — 非技术用户的一站式入口。描述你想要什么（或直接给 PRD 路径 + AI 部门配置路径），AI 负责从解析输入、初始化项目到上线的一切。
user_invocable: true
---

# /everything — 零技术门槛全流程向导

**这是非技术用户的专属入口。** 你只需要描述想要什么，或者直接给 PRD 和配置文件路径，其余全交给 AI。

---

## 触发条件

**意图判断**（满足任一即触发）：

- 用户输入 `/everything`
- 用户消息包含文件路径，且带有 `prd`、`配置`、`ai-team` 等上下文
- 用户**在描述一个想要开发/实现的功能或产品**，无论具体措辞如何

**不触发**：用户正在执行 `/project-flow`、`/deploy` 等其他技能；或用户只是在问技术问题而非提需求。

> 判断依据是**意图**，不是特定词语。"做个考勤系统"、"我们需要 XX 功能"、"能不能搭一个…"、"帮我实现…" 都应触发，不要等用户说出特定句式。

---

## AI 执行的完整流程

```
Phase -1. 输入解析      (识别路径格式，读 PRD，解析 ai-team-file 并就位)
Phase  1. 需求理解      (用你的语言重述需求，确认没误解)
Phase  2. 方案设计      (拆解任务，告诉你要做哪些事，等你点头)
Phase  0. 环境检查      (用户确认方案后才检查，缺什么告诉你找谁要)
Phase 0.5 项目初始化    (全新项目才执行：从 PRD 提取项目名、自动选部署路径)
Phase  3. 开发实现      (AI 自动写代码)
Phase  4. 本地验证      (AI 自动检查代码是否能运行)
Phase  5. 提交变更      (AI 生成提交记录，等你确认)
Phase  6. 部署上线      (AI 自动把代码推到服务器)
Phase  7. 验证结果      (AI 访问线上地址，确认功能跑通)
Phase  8. 告诉你结果    (清晰的总结报告 + 触发 /evolve)
```

---

## Phase -1 — 输入解析

**目标**：在任何事情之前，先弄清楚用户给了什么、把资源放到正确位置。

### -1.1 识别消息格式

扫描用户消息，判断是否包含路径：

```
用户消息包含 "prd：" 或 "需求文档：" 或 "prd:" → 提取路径，进入 -1.2
用户消息包含 "配置：" 或 "ai-team" 或 "ai_team"  → 提取路径，进入 -1.3
都不包含                                          → 跳过 -1.2/-1.3，进入 Phase 1
```

### -1.2 读取 PRD 文件

提取出 PRD 路径后：

```python
# 伪逻辑
path = 提取到的路径
if os.path.isfile(path):
    内容 = Read(path)         # 直接读文件
elif os.path.isdir(path):
    # 目录，找最可能是 PRD 的文件
    候选 = [README.md, PRD.md, 需求.md, prd.md, requirements.md, *.md 第一个]
    内容 = Read(第一个候选)
```

读完后，**把 PRD 内容暂存在上下文**，Phase 1 的需求理解直接从这里出发，不再重新问用户。

### -1.3 解析 ai-team-file 目录并就位

提取到 ai-team-file 路径后，列出目录内容：

```bash
ls -la <ai-team-file路径>/
```

按以下规则识别并复制到项目内：

| 识别规则 | 目标位置 |
|---------|---------|
| 文件名是 `.env`、`.env.docker.prod`、`env.prod`、`env.docker` | `./.env.docker.prod` |
| 文件名是 `deploy-config.md`、`config.md`、包含 `domain`/`port` 关键词的 `.md` | 暂存，Phase 0.5 读取 |

> **注意**：本服务器使用密码登录（root），无需 SSH 密钥。deploy.py 中已配置 `USE_PASSWORD = True`。

```bash
# 复制文件（举例，实际路径替换为检测到的路径）
cp <ai-team-file>/.env.docker.prod ./.env.docker.prod
```

**复制完成后**，向用户简短确认：

```
已从 ai-team-file 读取到：
✓ 生产配置 → 已就位
继续...
```

如果目录里有文件不认识，忽略它，不报错。
如果目录为空或路径不存在，告诉用户：

> ⚠️ `<路径>` 目录为空或不存在。请参考 `doc/ai-team-setup.md` 的「标准打包格式」部分，确认 AI 部门给的目录结构是否正确。

---

## Phase 1 → Phase 2 之后插入：Phase 0 — 环境检查

> **执行时机**：Phase 2 用户确认方案之后，Phase 3 开发开始之前。先聊清楚需求再检查环境，不要在用户刚开口描述需求时就抛出技术错误。

**目标**：确认所有前置条件就绪。缺少任何一项，停下来，告诉用户去哪里找、找谁要。

### 检查项 1：部署服务器连通性

本服务器使用密码登录，deploy.py 中已配置 `USE_PASSWORD = True`。无需 SSH 密钥。

验证服务器可连通：
```bash
python -c "import paramiko; c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy()); c.connect('47.121.130.229', username='root', password='P6ZxidTmtks!qPC', timeout=10); print('OK'); c.close()"
```

**如果连接失败**：
> ⚠️ 无法连接到部署服务器 47.121.130.229
>
> 请检查服务器是否在线，或联系管理员确认密码。

### 检查项 2：生产环境配置文件

```bash
ls .env.docker.prod 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

**如果 MISSING**（且 Phase -1.3 没有就位过）：

> ⚠️ 缺少生产环境配置 `.env.docker.prod`
>
> 同上，在 `doc/ai-team-setup.md` 的「生产环境配置文件」部分找说明，联系 AI 部门。

### 检查项 3：Anthropic API Key（如果项目用到 AI 功能）

读取 `.env.docker.prod`，检查 `ANTHROPIC_API_KEY` 是否有真实值（不是 `your-key-here`、`placeholder`、空字符串）。

**如果是 placeholder 或缺失**（需要判断本次需求是否涉及 AI 功能，不涉及则跳过）：

> ⚠️ Anthropic API Key 未配置。参考 `doc/ai-team-setup.md` 中「Anthropic API Key」部分联系 AI 部门获取。

### 所有检查通过

```
✓ SSH 密钥就绪
✓ 生产配置就绪
✓ API Key 已配置（或本次需求不涉及 AI）

环境检查通过。
```

---

## Phase 0.5 — 新项目初始化（仅全新项目执行）

**判断条件**（满足任一即为"全新项目"）：
- `git log --oneline | wc -l` 输出 ≤ 3（几乎没有提交历史）
- `deploy.py` 里 `PROJECT_NAME == "demo"` 或 `PUBLIC_DOMAIN == "demo.premom.tech"`（仍是模板默认值）
- Phase -1.3 读取到了 `deploy-config.md` 文件

**如果不是全新项目，跳过这个 phase。**

### 0.5.1 提取项目名

按优先级查找项目名：
1. Phase -1.3 读取到的 `deploy-config.md` 里有 `project_name` 或 `项目名` 字段
2. PRD 文件的第一个 `# 标题`
3. PRD 文件名本身（去掉扩展名）
4. 询问用户："这个项目叫什么名字？（1-3 个英文单词，用连字符，如 `customer-portal`）"

### 0.5.2 自动确定部署路径

**不询问用户，AI 自动判断**：

- Phase -1.3 读取到了 `deploy-config.md` 且包含域名/端口字段 → **路径 B（独立域名）**，直接读取配置
- 否则 → **路径 A（共享 demo）**，使用 `47.121.130.229:7005`，零配置继续

> 路径 B 的前提是 AI 部门已提前在 `deploy-config.md` 里写好域名/端口分配。没有这个文件就意味着没有独立域名，无需问用户。用户收到 `ai-team-file` 里有 `deploy-config.md` 时自然走路径 B，否则走路径 A 演示即可。

### 0.5.3 更新项目身份

根据上面收集到的信息，更新以下文件（AI 自动做，不需要用户操作）：

```python
# deploy.py 顶部常量
PROJECT_NAME = "<项目名>"
PUBLIC_DOMAIN = "47.121.130.229"  # A 路径保持 IP
FRONTEND_PORT = 7005              # A 路径保持 7005
BACKEND_PORT = 8006               # A 路径保持 8006

# docker-compose.prod.yml
container_name: <项目名>-frontend
container_name: <项目名>-backend
container_name: <项目名>-postgres
ports: "7005:80"
```

同时更新项目显示名（如果 PRD 有产品名的话）：
- `frontend/index.html` 的 `<title>`
- `frontend/src/components/AppLayout.tsx` 的顶栏标题
- `frontend/src/pages/LoginPage.tsx` 的登录页标题
- `backend/app/main.py` 的 `FastAPI(title="...")` 标题

完成后告知用户：

```
✓ 项目已初始化为「<项目名>」
✓ 部署地址：<域名>
```

---

## Phase 1 — 需求理解

**目标**：用非技术语言理解用户想要什么，不假设任何技术细节。

**如果 Phase -1.2 读取了 PRD**：
- 不要重新问"你想要什么"
- 直接基于 PRD 内容进行理解和提炼
- 只问 PRD 里没写清楚的部分（最多 2 个问题）

**如果没有 PRD**：
1. 听用户说需求（用户在 `/everything` 之后描述，或者 AI 主动问）
2. 只问高价值问题，最多 2-3 个，用**完全非技术**的语言：
   - ✅ "这个功能是给谁用的？"
   - ✅ "用户看到的界面大概长什么样？"
   - ✅ "这个数据需要保存下来吗？"
   - ❌ "你想用 REST 还是 GraphQL？"（技术问题，不要问）

**无论哪种方式**，最后都要重述需求，得到用户"对"/"就是这样"的确认才进 Phase 2。

---

## Phase 2 — 方案设计

**对用户完全透明，但不要让用户做技术决策。**

呈现一个**用非技术语言写的任务清单**，等用户确认：

```
我计划这样做：

1. 创建"客户留言"数据表（保存留言信息）
2. 创建填写表单的页面
3. 添加提交接口（把数据存进数据库）
4. 添加邮件通知功能
5. 把新页面加到导航菜单

预计需要约 15-20 分钟。

可以开始了吗？
```

**闸口**：等用户说"开始"、"好的"、"可以"之后才进入 Phase 3。

---

## Phase 3-7 — 开发到部署

直接调用 `/project-flow` 从 Step 3 开始执行（需求分析和方案设计已在 Phase 1-2 完成）。

在执行过程中：
- **不要展示代码给用户**（除非用户主动问）
- **不要问技术问题**（自己决定）
- **遇到障碍时用非技术语言解释**，然后告知解决方案

**遇到失败时的非技术语言示例**：
> ❌ 不好用："TypeScript type error: Property 'email' does not exist on type 'ContactForm'"
> ✅ 好用："代码检查发现一处问题，我正在修复，稍等。"

---

## Phase 8 — 结果报告与进化触发

用**完全非技术**的语言告知结果：

```
完成了！✓

你要的「客户留言表单」已经上线：
👉 http://47.121.130.229:7005/contact

功能验证：
✓ 页面可以正常访问
✓ 表单可以填写和提交
✓ 数据成功保存
✓ 邮件通知已发送测试

如果你发现任何问题，直接告诉我，我来修。
```

**发出报告后，等待用户反馈**：

- 用户说"好"/"可以"/"没问题"/"满意"，或 **30 秒内没有新消息** → 调用 `/evolve`（自动写入，不打扰用户；完成后仅一句话告知）
- 用户说"还有问题"/"这里不对" → 先修复，回到 Phase 3，修好后重新到 Phase 8
- 用户直接提下一个需求 → 跳过进化，直接从 Phase -1 开始新需求

---

## 重要原则

1. **用户永远不需要看代码** — 所有技术细节 AI 自己处理
2. **用户永远不需要做技术决策** — 遇到技术选择，AI 自己选最合适的
3. **文件路径直接处理，不要再问** — 用户给了路径就 Read，不要让用户再描述一遍
4. **环境不就绪时先停下来** — 不要假装能部署，先让用户把 `doc/ai-team-setup.md` 里的资源备齐
5. **新项目先初始化身份** — 不要用 demo 默认值部署新项目
6. **每个关键节点告知进度** — 用户不应该面对无声的等待

---

## 快捷方式

| 用户说 | AI 的反应 |
|--------|-----------|
| `prd：<路径>` | Phase -1 → 读文件 → 走全流程 |
| `prd：<路径>  配置：<路径>` | Phase -1 → 读PRD + 就位配置 → 走全流程 |
| "现在状态怎么样" | 检查服务器上的应用是否在运行（相当于 `/deploy --check`） |
| "上线" / "部署" | 跳过需求阶段，直接 Phase 0 → 6 |
| "有问题" / "出错了" | 先查日志，再用非技术语言解释，再修 |
| "重新开始" / "从头来" | 回到 Phase -1 |
