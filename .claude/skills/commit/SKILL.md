---
name: commit
description: 智能提交 — 分析 git 变更，自动生成 commit message、更新 CHANGELOG、记录开发要点。团队成员使用 /commit 触发。
user_invocable: true
---

# /commit — 智能提交与变更记录

当团队成员输入 `/commit` 时执行以下完整流程。

## 流程总览

```
1. 分析变更 → 2. 生成 commit message → 3. 更新 CHANGELOG.md
→ 4. (可选) 写入 dev-notes → 5. 提交
```

## Step 1: 分析变更

同时执行以下命令，收集变更全貌：

```bash
git status
git diff --staged
git diff
git log --oneline -5
```

如果没有任何修改（staged + unstaged 都为空），告知用户没有可提交的内容并终止。

如果有 unstaged 的修改，列出文件清单并询问用户：
> "以下文件有修改但未暂存，是否一并加入本次提交？"

根据用户选择执行 `git add <files>`。

**安全检查：** 扫描 staged 文件，如果包含 `.env`、`credentials`、API Key 等敏感内容，发出警告并要求确认。

## Step 2: 生成 Commit Message

根据 diff 内容，生成 Conventional Commits 格式的 commit message：

```
<type>(<scope>): <简短描述>

<详细说明（可选，仅在变更复杂时添加）>
```

**Type 规则：**
| type | 适用场景 |
|------|---------|
| feat | 新功能 |
| fix | Bug 修复 |
| refactor | 重构（不改变行为） |
| docs | 仅文档变更 |
| style | 代码格式（不影响逻辑） |
| perf | 性能优化 |
| test | 测试相关 |
| chore | 构建/依赖/配置 |
| infra | 基础设施/Docker/CI |

**Scope 规则：** 根据变更文件路径自动推断
- `backend/app/models.py` → `model`
- `backend/app/routers/` → `api`
- `backend/app/services/` → `service`
- `backend/app/schemas.py` → `schema`
- `frontend/src/pages/` → `page`
- `frontend/src/components/` → `component`
- `frontend/src/api/` → `api-client`
- `tests/` → `test`
- `docker-compose*.yml` / `Dockerfile` → `infra`
- 多个 scope 时用逗号分隔，如 `feat(api,model)`

将生成的 message 展示给用户确认或修改。

## Step 3: 更新 CHANGELOG.md

在 `doc/CHANGELOG.md` 文件**第一个 `---` 分隔符之后**插入新记录：

```markdown
## [YYYY-MM-DD] <commit message 第一行>

**Files changed:**
- `<file path>` — <简要说明该文件的变更>

**Details:**
- <变更的业务上下文和原因，1-3 条>

---
```

注意：
- 日期使用当天日期
- Files changed 按变更文件逐条列出
- Details 侧重 **为什么改** 而不是 **改了什么**

## Step 4: 写入开发要点（按需）

**判断条件 — 满足任一即触发：**
- 新增了数据库表或字段（即使是 entrypoint.sh 里加的 ALTER）
- 引入了新的第三方依赖
- 变更了架构模式（如新增中间件、改变认证方式）
- 修复了非显而易见的 bug
- 涉及兼容性处理或 workaround

**触发时：** 在 `doc/dev-notes/` 创建文件，命名格式：`YYYY-MM-DD-<slug>.md`

```markdown
# <标题>

**日期:** YYYY-MM-DD
**作者:** <从 git config user.name 获取>
**关联提交:** <commit hash 前 7 位>

## 背景
<为什么做这个变更>

## 决策 / 要点
<做了什么架构决策，为什么选择这个方案>

## 影响范围
<这个变更影响了哪些模块>

## 相关文件
- `<file1>` — <说明>
```

## Step 5: 提交

将所有变更一次性提交：

```bash
git add <原始变更文件>
git add doc/CHANGELOG.md
git add doc/dev-notes/<new-file>.md   # 如果有
git commit -m "<commit message>"
```

提交完成后显示：
- commit hash
- 变更文件数和行数统计
- 提示用户是否需要 `git push`

## 重要约束

1. **不要自动 push** — 只提交到本地，push 由用户决定
2. **不要提交 .env / ai-team-key 等敏感文件** — 发现时警告用户
3. **commit message 必须让用户确认** — 不要静默提交
4. **CHANGELOG 条目必须有 Details** — 不能只列文件不写原因
5. **保持幂等** — 如果用户中途取消后再次执行，不会产生重复记录
