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
| 对外域名 | **http://47.121.130.229:7005/** |
| 前端直连 | http://47.121.130.229:7005 |
| 后端直连 | http://47.121.130.229:7005 |
| 容器名 | `demo-frontend` / `demo-backend` / `demo-postgres` |
| 部署路径 | `/root/demo` |
| 反代原理 | nginx 把 `47.121.130.229:7005` 反代到前端容器 |

> **关键约束**：前端容器必须把 `7005:80` 映射到宿主。只要 `docker-compose.prod.yml` 的 `ports` 保留 `"7005:80"`，服务就通。
>
> **注意**：demo 槽位是共享的测试环境 — 整个团队只能同时部署一个 demo 项目。正式项目需要自己的域名+端口（见下方「独立部署配置」）。

## 服务器连接

| 项目 | 值 |
|------|-----|
| 服务器 | `47.121.130.229` (root) |
| 登录方式 | **密码登录**（root / 服务器密码） |
| SSH 密钥 | 本服务器不使用密钥，使用密码 |
| 连接命令 | `ssh -o StrictHostKeyChecking=no root@47.121.130.229` |

**首次使用**：确保 deploy.py 中的密码配置正确（`SSH_PASSWORD` 环境变量或代码中配置）。

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
cd /root/demo && sudo docker compose -f docker-compose.prod.yml up -d --build --force-recreate 2>&1 | tail -20
```

**`--seed`**：
```bash
sudo docker exec demo-backend python seed.py
```

**`--logs`**：
```bash
cd /root/demo && sudo docker compose -f docker-compose.prod.yml logs --tail=50
```

### Step 4: 验证

```bash
curl -sf --max-time 10 http://47.121.130.229:7005/health
curl -sf --max-time 10 -o /dev/null -w "HTTP %{http_code}" http://47.121.130.229:7005/
# 直连验证
curl -sf --max-time 10 http://47.121.130.229:7005/health
```

### Step 5: 输出结果

```
部署完成 ✓
  地址: http://47.121.130.229:7005/ — HTTP 200
  后端: http://47.121.130.229:7005/health — healthy
  耗时: ~2m30s
```

## 独立部署配置（非 demo 槽位）

想部署到自己的域名 + 端口（不影响 demo）：

1. **改 `deploy.py` 顶部常量**：
   ```python
   PROJECT_NAME = "myapp"
   PUBLIC_DOMAIN = "myapp.yourdomain.com"  # 或你自己的域名
   FRONTEND_PORT = 7005                    # 服务器上必须未被占用
   BACKEND_PORT = 8006
   ```

2. **改 `docker-compose.prod.yml`**：
   - `container_name: myapp-frontend` / `myapp-backend` / `myapp-postgres`
   - `ports: "9701:80"` / `"8007:8000"`

3. **域名 DNS**：在 DNS 服务商加 A 记录 `<你的域名>` → `16.146.108.197`

4. **服务器 nginx**：如需域名访问，请管理员在服务器上加 nginx 配置，把请求反代到 `172.17.0.1:7005`。

## 错误处理

| 错误 | 处理 |
|------|------|
| SSH 密码未设置 | 设置环境变量 `export SSH_PASSWORD="你的密码"`，或修改 `deploy.py` 中的默认值 |
| 连接超时 / 拒绝 | 检查 `47.121.130.229` 是否可达，安全组是否放行 22 端口 |
| Docker 权限错误 | 命令前加 sudo |
| 构建失败（TypeScript） | 本地跑 `cd frontend && npm run build` 复现并修复 |
| 构建失败（Python） | 检查 `requirements.txt` 依赖是否齐全 |
| 磁盘不足 | 建议运行 `docker image prune -f` |
| 前端 unhealthy | 等待更久或查看 `docker logs demo-frontend` |
| `47.121.130.229:7005` 返回 502 | 检查前端容器是否跑起来且把端口暴露到宿主：`sudo docker ps \| grep demo-frontend` |
| 端口撞车（7005/8006 被占用） | 改 `deploy.py` 和 `docker-compose.prod.yml` 的端口 + 走「独立部署」路径 |

## 重要提醒

- 不要把服务器密码提交到 git
- `.env.docker.prod` 包含生产密钥，deploy.py 会自动复制为 `.env.docker`
- 部署不会丢失数据库数据（PostgreSQL 使用 Docker volume）
- **demo 槽位是单例** — 新部署会覆盖旧部署。团队协作时先对一下谁在用 demo
- **独立部署** 需要管理员在 EC2 上加域名 nginx 配置，无法完全自动化
