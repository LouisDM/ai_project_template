---
name: project-flow
description: 项目全流程编排 — 需求分析 → 方案设计 → 开发 → 本地验证 → 部署 → 部署后测试。用户描述一个需求或功能时调用，Claude 按流程逐阶段推进并在关键节点等待用户确认。
user_invocable: true
---

# /project-flow — 项目全流程编排

当用户描述一个需求（新功能、新页面、新接口），调用此 skill 走完整流程。

**本 skill 是编排器**，自身不干活，它的职责是**按序调度已有 skill / 工具**并在关键闸口停下来让用户拍板。

## 完整流程

```
Step 1. 需求分析      (读代码 + brainstorming + 澄清)
Step 2. 方案设计      (写计划 + 拆任务)
Step 3. 开发实现      (按任务逐个做)
Step 4. 本地验证      (typecheck + 启动 + 自测)
Step 5. 提交变更      (调用 /commit)
Step 6. 部署上线      (调用 /deploy)
Step 7. 部署后测试    (调用 /test-deploy)
Step 8. 最终报告      (给用户总结)
```

## 各阶段规范

### Step 1 — 需求分析

**目标**：把用户描述翻译成具体的技术任务。

做什么：
1. **读代码了解现状**：至少读 `CLAUDE.md`、`backend/app/main.py`、`frontend/src/App.tsx`、相关的 `models.py`/`routers/` 目录
2. **识别关键问题**：用户有没有说清楚数据模型？UI 交互形态？权限控制？
3. **用 `AskUserQuestion` 澄清**：最多问 2-3 个高杠杆问题（不要一次问 10 个）
4. **重述需求**：用自己的话复述给用户听，得到 yes/no 确认才进入 Step 2

**不要做的事**：
- 不要直接动代码
- 不要假设用户省略的细节（要问）
- 不要跳过澄清直接进入方案设计

### Step 2 — 方案设计

**目标**：拆出有序的、可独立交付的技术任务。

做什么：
1. 用 `TaskCreate` 拆 3-8 个任务（每个 ≤ 1 小时工作量）
2. 每个任务写清楚：要改哪些文件、引入什么新依赖、是否要数据库迁移
3. 如果需要新表/字段：在任务描述里写好 `ALTER TABLE ... IF NOT EXISTS` 迁移片段
4. **输出一个简短的方案摘要**给用户看，等用户说"开始做"或改方向

**闸口**：必须用户确认方案后才能进入 Step 3。

### Step 3 — 开发实现

**目标**：按任务列表逐个完成，边做边 `TaskUpdate` 状态。

做什么：
1. 每个任务开始前 `TaskUpdate status=in_progress`
2. 做完立即 `TaskUpdate status=completed`
3. 遵守 `CLAUDE.md` 里的技术栈约定（FastAPI + async SQLAlchemy + React + Antd）
4. 新增模型时同步改：`models.py` + `schemas.py` + `routers/` + `main.py 注册` + `entrypoint.sh 迁移`
5. 新增前端页面时同步改：`pages/` + `App.tsx 路由` + `components/AppLayout.tsx 菜单`

**停下来等用户确认的情况**：
- 方案实施中遇到无法决策的取舍
- 任务涉及删除数据或破坏性变更

### Step 4 — 本地验证

**目标**：在本地把所有能发现的问题发现完。

做什么（并行执行）：
```bash
cd frontend && npx tsc --noEmit    # 前端类型检查
cd frontend && npx vite build      # 确认能打包（Docker 里跑的是这个）
cd backend && python -c "from app.main import app; print('OK')"  # 后端 import 正常
```

如有现成单元测试：`cd backend && pytest` 跑一遍。

**任何一个失败都必须修到绿**，不能带问题进入 Step 5。

### Step 5 — 提交变更

**目标**：把代码进 git，生成有意义的提交记录。

调用 `/commit` skill，它会：
- 分析 diff 生成 conventional commits message
- 更新 `doc/CHANGELOG.md`
- 涉及迁移/新依赖时写 `doc/dev-notes/` 记录

**闸口**：用户确认 commit message 后才执行。

### Step 6 — 部署上线

**目标**：把本地代码上线到生产（默认 demo 槽位）。

调用 `/deploy` skill，等它输出"部署完成"+健康检查 200。

失败的典型原因：
- Docker 镜像构建失败（前端 `npm run build` 错误） — 回 Step 4 补修
- 数据库迁移失败 — 检查 `entrypoint.sh` 的 ALTER 语句
- 端口冲突 — 可能 `FRONTEND_PORT`/`BACKEND_PORT` 被占了

### Step 7 — 部署后测试

**目标**：验证生产环境关键路径真能跑。

调用 `/test-deploy` skill，跑接口 + 页面冒烟。

失败时：
1. **不要回滚**（除非明确破坏生产）
2. **立即报给用户**具体是哪一步失败、失败响应是什么
3. 讨论修复方案再进入下一轮

### Step 8 — 最终报告

**目标**：一次性告诉用户都做了什么、效果如何。

模板：
```
需求：<用户一句话重述>

完成的工作：
- 后端：<改了什么>（<行数> 行）
- 前端：<改了什么>（<行数> 行）
- 数据库：<加了什么表/字段>

部署：
- 域名：https://demo.premom.tech/
- commit：<hash>
- 耗时：<X> 分钟

测试结果：
- 接口冒烟：9/9 通过
- 页面冒烟：3/3 通过

下一步建议：
- <如果有遗留、后续优化>
```

## 触发条件

用户说类似下面的话时，调用 `/project-flow`：
- "帮我做一个 XX 功能"
- "加一个 YY 页面"
- "用户反馈说 ZZ，帮我改一下"
- 任何以"需求"、"新功能"、"帮我实现"开头的请求

## 例外情况

**不走全流程**的情形：
- 纯 bug 修复（一行/一函数的改动）→ 直接改 + `/commit`
- 仅文档改动 → 直接改 + `/commit`
- 配置调整（env、nginx）→ 直接改 + 手动验证

**快速通道**：用户明确说"不走流程，直接改" → 尊重用户，跳过本 skill。

## 重要约束

1. **闸口必须停**：Step 1 → 2 和 Step 2 → 3 之间等用户确认，不要一路自己飞
2. **不要跳步**：不能从 Step 3 直接跳到 Step 6，必须经过 Step 4 本地验证
3. **失败不隐瞒**：任何 step 失败都要立即告诉用户，不要装作成功
4. **一次只专注一个需求**：如果用户中途丢新需求，先把当前的做完或显式暂停
