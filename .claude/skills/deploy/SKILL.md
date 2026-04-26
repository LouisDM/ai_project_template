---
name: deploy
description: 一键部署当前项目到 EC2 服务器 — 打包、传输、构建、验证全自动。支持 /deploy、/deploy --check、/deploy --rebuild 等参数。
user_invocable: true
---

# /deploy — 一键部署到 EC2

当用户输入 `/deploy` 时执行以下流程，将当前项目部署到 EC2 服务器（**SSH 直连 + nginx 二级域名反代**）。

## 动态端口 + 二级域名分配

deploy.py 已支持自动分配端口和域名：

| 项目 | 值 |
|------|-----|
| 端口范围 | 22222-22333（前端），后端 = 前端 + 1 |
| 域名格式 | `\u003c项目名\u003e.demo.intelliastra.com` |
| 自动分配 | 部署时自动扫描可用端口，自动生成 nginx 配置 |
| 容器名 | `\u003c项目名\u003e-frontend` / `\u003c项目名\u003e-backend` / `\u003c项目名\u003e-postgres` |
| 部署路径 | `/root/\u003c项目名\u003e` |

> **不需要手动修改端口或域名** — deploy.py 会自动处理一切。如需指定端口/域名，见下方「自定义参数」。

## 服务器连接

| 项目 | 值 |
|------|-----|
| 服务器 | `47.121.130.229` (root) |
| 登录方式 | **密码登录**（root / 服务器密码） |
| SSH 密钥 | 本服务器不使用密钥，使用密码 |
| 连接命令 | `ssh -o StrictHostKeyChecking=no root@47.121.130.229` |

**首次使用**：确保 deploy.py 中的密码配置正确（`SSH_PASSWORD` 环境变量或代码中配置）。

## 参数支持

- `/deploy` — 完整部署（自动分配端口和域名）
- `/deploy --check` — 仅检查服务器状态，不部署
- `/deploy --rebuild` — 强制重建所有容器（不重新传输文件）
- `/deploy --seed` — 部署后执行数据库种子脚本
- `/deploy --logs` — 查看容器日志

## 自定义参数（可选）

如需指定端口或域名（不推荐，除非有特殊需求）：

```bash
python deploy.py --port 22222 --domain myapp.demo.intelliastra.com --name myapp
```

参数说明：
- `--port`: 指定前端端口（后端自动用 +1）
- `--domain`: 指定完整二级域名
- `--name`: 指定项目名（影响容器名和部署目录）

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
cd /root/<项目名> && sudo docker compose -f docker-compose.prod.yml up -d --build --force-recreate 2>&1 | tail -20
```

**`--seed`**：
```bash
sudo docker exec <项目名>-backend python seed.py
```

**`--logs`**：
```bash
cd /root/<项目名> && sudo docker compose -f docker-compose.prod.yml logs --tail=50
```

### Step 4: 验证

```bash
# 通过域名验证（nginx 反代）
curl -sf --max-time 10 -o /dev/null -w "HTTP %{http_code}" http://<分配的域名>/
# 直连验证
curl -sf --max-time 10 -o /dev/null -w "HTTP %{http_code}" http://<服务器IP>:<前端端口>/
```

### Step 5: 输出结果

```
部署完成 ✓
  域名入口: http://myproject.demo.intelliastra.com/ — HTTP 200
  前端直连: http://47.121.130.229:22222/
  后端直连: http://47.121.130.229:22223/
  耗时: ~2m30s
```

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
| 域名返回 502 | 检查 nginx 配置是否正确 + 前端容器是否运行：`sudo docker ps \| grep <项目名>-frontend` |
| 端口被占用 | deploy.py 会自动扫描并分配下一个可用端口，如手动指定需确保未被占用 |

## 重要提醒

- 不要把服务器密码提交到 git
- `.env.docker.prod` 包含生产密钥，deploy.py 会自动复制为 `.env.docker`
- 部署不会丢失数据库数据（PostgreSQL 使用 Docker volume）
- **每个项目独立端口和域名** — 多个项目可同时部署，互不干扰
- **域名通配符** — `*.demo.intelliastra.com` 已指向服务器，无需额外 DNS 配置
