---
name: test-deploy
description: 部署完成后的自动化冒烟测试 — 包括接口冒烟测试（httpx）和页面冒烟测试（Playwright MCP）。验证生产环境关键路径可用。用户使用 /test-deploy 触发。
user_invocable: true
---

# /test-deploy — 部署后自动化冒烟测试

当用户输入 `/test-deploy` 时，跑一套"快速可信"的生产冒烟测试，验证刚部署的服务能真正响应。

## 测试目标

不是完整回归，而是**关键路径烟雾测试**，目标 ≤ 2 分钟出结果：

1. **基础设施** — HTTPS 域名可达、SSL 有效、/health 返回 200
2. **接口层** — 认证、读/写 CRUD 往返成功
3. **页面层** — 登录 → 受保护页面 → 基础操作闭环

发现问题时**不要继续往下跑**，立即把失败原因报告给用户。

## 执行流程

### Step 1: 读取部署配置

从 `deploy.py` 顶部常量获取测试目标，**不要硬编码**：

```bash
python -c "
import ast, sys
src = open('deploy.py', encoding='utf-8').read()
tree = ast.parse(src)
consts = {n.targets[0].id: ast.literal_eval(n.value)
          for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.value, (ast.Constant, ast.Str))}
for k in ('PUBLIC_DOMAIN','EC2_HOST','FRONTEND_PORT','BACKEND_PORT'):
    print(f'{k}={consts.get(k, \"\")}')"
```

得到：
- `HTTP_URL = http://47.121.130.229:7005`
- `BACKEND_URL = http://47.121.130.229:7005`（直连后端，跳过 nginx）

### Step 2: 接口冒烟测试

运行 `tests_e2e/api_smoke.py`（模板已附带）：

```bash
python tests_e2e/api_smoke.py --base-url http://47.121.130.229:7005
```

脚本内容覆盖：
- `GET /health` → 200, `{"status":"ok"}`
- `POST /api/auth/login` 用 admin/admin123 → 200 + token
- `GET /api/items/` → 200（列表）
- `POST /api/items/` → 201（创建测试 item）
- `GET /api/items/` → 列表包含刚创建的 item
- `DELETE /api/items/{id}` → 204（清理）

**任意一步失败立即退出 non-zero**，并打印失败的具体请求+响应。

若 `admin/admin123` 不存在：提示用户运行 `python deploy.py --seed` 或在服务器上 `sudo docker exec {project}-backend python seed.py`。

### Step 3: 页面冒烟测试（Playwright MCP）

如果 `mcp__plugin_ecc_playwright__browser_*` 工具可用，走真实浏览器：

1. **打开首页**：`mcp__plugin_ecc_playwright__browser_navigate` → `http://47.121.130.229:7005/`
2. **断言跳转到 /login**：`browser_snapshot` 检查 URL 和登录表单存在
3. **填表登录**：
   - 用户名输入 `admin`
   - 密码输入 `admin123`
   - 点击"登录"按钮
4. **断言跳转到首页**：URL 变成 `/`，看到 "Items" 页面的"新建"按钮
5. **点击"新建"**：打开表单 Modal
6. **填表并提交**：title = `SMOKE_TEST_{timestamp}`，点"确认"
7. **断言列表里出现新记录**：`browser_snapshot` 包含 SMOKE_TEST_{timestamp} 文本
8. **清理**：点刚创建的那行的"删除"按钮，确认删除

如果 Playwright MCP 不可用（比如命令行场景），fallback 到只跑 Step 2 的接口测试，并明确告诉用户"页面测试未执行 — 请人工确认"。

### Step 4: 出具报告

无论成功失败，最后打印一个结构化报告：

```
部署后冒烟测试 — 47.121.130.229:7005
───────────────────────────────
[✓] HTTPS 可达                    200 OK  (142ms)
[✓] GET /health                   200 OK
[✓] POST /api/auth/login          200, token=eyJ...
[✓] GET /api/items/ (列表)        200, 0 items
[✓] POST /api/items/ (创建)       201, id=42
[✓] GET /api/items/ (验证)        200, 包含 id=42
[✓] DELETE /api/items/42          204
[✓] UI: 登录 → 首页                 ✓
[✓] UI: 新建 Item                   ✓
[✓] UI: 删除 Item                   ✓
───────────────────────────────
全部通过 (9/9) · 耗时 47s
```

或者失败时：

```
[✗] POST /api/auth/login          401 Unauthorized
    请求: {"username":"admin","password":"admin123"}
    响应: {"detail":"Invalid credentials"}
    建议: 运行 python deploy.py --seed 创建 admin 账号
───────────────────────────────
失败，终止后续步骤
```

## 重要约束

- **不要污染生产数据** — 创建的测试记录必须带明显标记（如 `SMOKE_TEST_` 前缀）并在测试结束时删除
- **不要连续并发测试** — 一轮测试逐步走，避免竞态
- **不要用生产账号** — 只用 seed 出来的 `admin` 账号；真实用户不测试
- **超时短** — 每个接口请求 ≤ 10s 超时，测试总体目标 ≤ 2 分钟
- **测试失败等于部署失败** — 立即告诉用户，不要假装成功
