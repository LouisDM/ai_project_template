# 部署后测试

本目录存放**生产环境冒烟测试**（不是单元测试）— 部署完成后跑一遍，验证关键路径没挂。

由 `/test-deploy` skill 自动调用，也可手动跑。

## 依赖

```bash
pip install httpx
```

Playwright 页面测试走 Claude Code 的 Playwright MCP，不需要本地安装。

## 手动运行

**纯接口测试**（2 分钟内搞定）：
```bash
python tests_e2e/api_smoke.py --base-url https://demo.premom.tech
```

**指定账号**：
```bash
python tests_e2e/api_smoke.py --base-url https://demo.premom.tech --username admin --password yourpass
```

**跳过 HTTPS，直连后端调试**：
```bash
python tests_e2e/api_smoke.py --base-url http://cms.premom.tech:8006
```

## 测试覆盖

| 层 | 检查项 |
|----|--------|
| 基础设施 | HTTPS/TLS 有效，`/health` 返回 200 |
| 认证 | `/api/auth/login` 往返 token |
| CRUD | `/api/items/` 列表、创建、验证、删除 |
| 前端（Playwright） | 登录 → 首页 → 新建 Item → 删除（需 `/test-deploy` skill） |

## 扩展新测试

每加一个关键业务路径（比如"提交订单"），就加一个 `api_<path>.py`：

```python
# tests_e2e/api_order.py
from api_smoke import _step, expect, httpx

def test_order_flow(base_url: str, token: str):
    ...
```

然后在 `/test-deploy` SKILL.md 的测试序列里加一行调用。

## 约定

- 测试数据**必须**带 `SMOKE_TEST_` 前缀便于识别
- **结束时清理**，不要留垃圾在生产库
- 任意步骤失败立即 `sys.exit(1)`，不要静默继续
