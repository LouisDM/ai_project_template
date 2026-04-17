---
name: deploy
description: 一键部署当前项目到 EC2 服务器 — 打包、传输、构建、验证全自动。支持 /deploy、/deploy --check、/deploy --rebuild 等参数。
user_invocable: true
---

# /deploy — 一键部署到 EC2

当用户输入 `/deploy` 时执行以下流程，将当前项目部署到 EC2 服务器（**SSH 直连 + gateway-nginx HTTPS 反代**）。

## 默认 demo 测试槽位

**开箱即用的测试环境**（无需改任何配置）：

| 项目 | 值 |
|------|-----|
| 对外域名 | **https://demo.premom.tech/**（HTTPS，泛域名证书） |
| 前端直连 | http://cms.premom.tech:9700 |
| 后端直连 | http://cms.premom.tech:8006 |
| 容器名 | `demo-frontend` / `demo-backend` / `demo-postgres` |
| 部署路径 | `/home/ec2-user/demo` |
| 反代原理 | gateway-nginx 把 `demo.premom.tech` 反代到 `172.17.0.1:9700`（Docker 网桥 + 宿主端口） |

> **关键约束**：前端容器必须把 `9700:80` 映射到宿主。只要 `docker-compose.prod.yml` 的 `ports` 保留 `"9700:80"`，域名就通。
>
> **注意**：demo 槽位是共享的测试环境 — 整个团队只能同时部署一个 demo 项目。正式项目需要自己的域名+端口（见下方「独立部署配置」）。

## 服务器连接

| 项目 | 值 |
|------|-----|
| EC2 | `cms.premom.tech` (ec2-user) |
| SSH 密钥 | `<项目>/ssh/ai-team-key`（推荐），也支持 `D:\ssh\ai-team-key` 或 `AI_TEAM_SSH_KEY` 环境变量 |
| 连接命令 | `ssh -i ./ssh/ai-team-key -o StrictHostKeyChecking=no ec2-user@cms.premom.tech` |

**首次使用**：向团队管理员获取 `ai-team-key` 私钥，放到 `<项目>/ssh/ai-team-key`（`.gitignore` 已忽略该目录，不会提交）。

## 参数支持

- `/deploy` — 完整部署（打包 → 传输 → 构建 → 自动接入 gateway → 验证）
- `/deploy --check` — 仅检查服务器状态，不部署
- `/deploy --rebuild` — 强制重建所有容器（不重新传输文件）
- `/deploy --seed` — 部署后执行数据库种子脚本
- `/deploy --logs` — 查看容器日志

## 执行流程

### Step 1: 前置检查

```bash
cd <project_root> && git status --short
```

如果有未提交的变更，**提醒用户**但不阻止部署。

### Step 2: 执行部署脚本

```bash
cd <project_root> && python deploy.py -y
```

`deploy.py` 自动完成：
1. 打包项目文件（排除 node_modules/.git/uploads 等）
2. SFTP 上传到 EC2
3. 解压 + `docker compose up -d --build`
4. 验证 `/health` + 前端状态（域名直接通，无需额外网络配置）

### Step 3: 参数处理

**`--rebuild`**（直接在服务器上重建，不重传）：
```bash
cd /home/ec2-user/demo && sudo docker compose -f docker-compose.prod.yml up -d --build --force-recreate 2>&1 | tail -20
```

**`--seed`**：
```bash
sudo docker exec demo-backend python seed.py
```

**`--logs`**：
```bash
cd /home/ec2-user/demo && sudo docker compose -f docker-compose.prod.yml logs --tail=50
```

### Step 4: 验证

```bash
curl -sf --max-time 10 https://demo.premom.tech/health
curl -sf --max-time 10 -o /dev/null -w "HTTP %{http_code}" https://demo.premom.tech/
# 直连验证
curl -sf --max-time 10 http://cms.premom.tech:8006/health
```

### Step 5: 输出结果

```
部署完成 ✓
  域名: https://demo.premom.tech/ — HTTP 200
  后端: http://cms.premom.tech:8006/health — healthy
  耗时: ~2m30s
```

## 独立部署配置（非 demo 槽位）

想部署到自己的域名 + 端口（不影响 demo）：

1. **改 `deploy.py` 顶部常量**：
   ```python
   PROJECT_NAME = "myapp"
   PUBLIC_DOMAIN = "myapp.premom.tech"     # 或你自己的域名
   FRONTEND_PORT = 9701                    # 服务器上必须未被占用
   BACKEND_PORT = 8007
   ```

2. **改 `docker-compose.prod.yml`**：
   - `container_name: myapp-frontend` / `myapp-backend` / `myapp-postgres`
   - `ports: "9701:80"` / `"8007:8000"`

3. **域名 DNS**：在 DNS 服务商加 A 记录 `<你的域名>` → `16.146.108.197`

4. **服务器 nginx**：请管理员登录 EC2 加一份 `/opt/gateway/nginx/conf.d/<你的域名>.conf`，参考 `demo.premom.tech.conf`，把 `proxy_pass http://172.17.0.1:9700;` 里的端口改成你的 `FRONTEND_PORT`。

## 错误处理

| 错误 | 处理 |
|------|------|
| SSH 私钥找不到 | 提示用户向团队管理员获取 `ai-team-key`，放到项目根目录下的 `ssh/ai-team-key` |
| 连接超时 / 拒绝 | 检查 `cms.premom.tech` 是否可达，安全组是否放行 22 端口 |
| Docker 权限错误 | 命令前加 sudo |
| 构建失败（TypeScript） | 本地跑 `cd frontend && npm run build` 复现并修复 |
| 构建失败（Python） | 检查 `requirements.txt` 依赖是否齐全 |
| 磁盘不足 | 建议运行 `docker image prune -f` |
| 前端 unhealthy | 等待更久或查看 `docker logs demo-frontend` |
| `demo.premom.tech` 返回 502 | 检查前端容器是否跑起来且把 `9700:80` 暴露到宿主：`sudo docker ps \| grep demo-frontend` 应该看到 `0.0.0.0:9700->80/tcp` |
| 端口撞车（9700/8006 被占用） | 改 `deploy.py` 和 `docker-compose.prod.yml` 的端口 + 走「独立部署」路径 |

## 重要提醒

- 不要把 `ai-team-key` 私钥提交到 git（已在 `.gitignore` 中忽略）
- `.env.docker.prod` 包含生产密钥，deploy.py 会自动复制为 `.env.docker`
- 部署不会丢失数据库数据（PostgreSQL 使用 Docker volume）
- **demo 槽位是单例** — 新部署会覆盖旧部署。团队协作时先对一下谁在用 demo
- **独立部署** 需要管理员在 EC2 上加域名 nginx 配置，无法完全自动化
