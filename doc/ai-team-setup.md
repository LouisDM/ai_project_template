# AI 部门资源获取指南

**本文档面向非技术团队成员。** 在使用 `/everything` 命令部署项目前，需要先从 AI 部门获取以下资源。每一项都有说明：是什么、为什么需要、怎么要。

---

## 快速检查清单

在开始前，把以下清单发给 AI 部门，请他们帮你确认哪些已就绪：

```
我正在使用 AI 项目模板，准备上线一个功能。
请帮我确认以下资源是否已准备好：

[ ] 1. SSH 部署密钥（ai-team-key 文件）
[ ] 2. 生产环境配置文件（.env.docker.prod）
[ ] 3. Anthropic API Key（如果项目有 AI 功能）
[ ] 4. 项目域名（如果需要独立域名）

项目名：_____________
```

---

## 资源 1：SSH 部署密钥

**是什么**：一个叫 `ai-team-key` 的文件，是连接服务器的"数字钥匙"。没有它，代码无法上传到服务器。

**为什么 AI 部门统一管理**：这个密钥可以直接访问公司服务器，必须严格保管，不能随意分发或提交到代码仓库。

**怎么要**：把以下内容发给 AI 部门：

> 你好，我需要 `ai-team-key` 文件用于项目部署。
> 项目名：[你的项目名]
> 我会把它放在本地项目的 `ssh/` 文件夹里，不会上传到 git。

**收到后怎么放**：

```
你的项目文件夹/
└── ssh/
    └── ai-team-key   ← 放这里（文件名必须是这个）
```

> ⚠️ 注意：这个文件千万不要通过微信/邮件转发给他人，也不要上传到任何云盘。如果误操作了，立即联系 AI 部门更换密钥。

---

## 资源 2：生产环境配置文件

**是什么**：一个叫 `.env.docker.prod` 的文件，里面包含数据库密码、加密密钥等敏感配置。

**为什么需要**：应用运行需要数据库，数据库需要密码，这些密码必须由 AI 部门设置，不能使用默认值。

**怎么要**：把以下内容发给 AI 部门：

> 你好，我需要项目的 `.env.docker.prod` 配置文件。
>
> 项目名：[你的项目名]
> 部署环境：demo 测试槽位（或 独立域名 ___）
>
> 请帮我生成或填写以下字段：
> - POSTGRES_PASSWORD（数据库密码）
> - SECRET_KEY（应用加密密钥）
> - ANTHROPIC_API_KEY（如需要 AI 功能）

**AI 部门操作方式**（供 AI 部门参考）：

```bash
# 复制模板并填写真实值
cp .env.docker.example .env.docker.prod

# 需要填写的字段：
POSTGRES_PASSWORD=<随机生成的强密码>
SECRET_KEY=<随机生成的32位以上密钥>
ANTHROPIC_API_KEY=<从 Anthropic 控制台获取>
```

**收到后怎么放**：直接放在项目根目录，文件名为 `.env.docker.prod`。

> ⚠️ 注意：同上，这个文件包含密码，不要上传到 git 或发给无关人员。

---

## 资源 3：Anthropic API Key

**是什么**：一串以 `sk-ant-` 开头的字符串，是调用 Claude AI 的授权凭证。

**什么情况下需要**：你的项目包含 AI 对话、AI 分析、AI 生成内容等功能时需要。如果项目只是普通的增删改查，可以暂时不需要。

**怎么要**：把以下内容发给 AI 部门：

> 你好，我的项目 [项目名] 有 AI 功能，需要一个 Anthropic API Key。
> 这个 Key 会放在生产配置文件里，仅用于这个项目。

**AI 部门说明**（供 AI 部门参考）：
- 在 [Anthropic Console](https://console.anthropic.com/) 创建或分配一个 API Key
- 建议为每个项目创建单独的 Key，便于用量追踪和权限控制
- 把 Key 填入项目的 `.env.docker.prod` 文件的 `ANTHROPIC_API_KEY` 字段

---

## 资源 4：项目域名（独立部署时才需要）

**什么情况下需要**：
- 默认 demo 槽位（`demo.premom.tech`）是共享的，整个团队只能同时跑一个。
- 如果你需要长期运行、不被他人覆盖，需要申请一个独立域名。

**是什么**：一个子域名（如 `myproject.premom.tech`）+ 服务器上的 nginx 配置。

**怎么要**：

> 你好，我的项目 [项目名] 需要一个独立域名，不占用 demo 槽位。
>
> 建议域名：[你的项目名].premom.tech（或其他你想要的）
>
> 需要 AI 部门完成：
> 1. 在 EC2 服务器上添加 nginx 配置，把域名指向我的应用端口
> 2. 告诉我应该在 `deploy.py` 里填什么端口号

**AI 部门操作方式**（供 AI 部门参考）：

1. 选一个未被占用的端口（前端 970x，后端 800x）
2. 在 EC2 的 `/opt/gateway/nginx/conf.d/` 目录下创建配置文件：

```nginx
# /opt/gateway/nginx/conf.d/<域名>.conf
server {
    listen 80;
    server_name <域名>;
    location / {
        proxy_pass http://172.17.0.1:<前端端口>;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. 重新加载 nginx：`sudo nginx -s reload`
4. 把域名和端口告知项目负责人，他们填入 `deploy.py`：

```python
PROJECT_NAME = "<项目名>"
PUBLIC_DOMAIN = "<域名>"
FRONTEND_PORT = <前端端口>
BACKEND_PORT = <后端端口>
```

---

## 联系方式

| 需要帮助 | 找谁 |
|---------|------|
| SSH 密钥、服务器权限 | AI 部门管理员 |
| API Key、模型额度 | AI 部门负责人 |
| 域名配置、nginx | AI 部门运维 |
| 应用功能问题 | 直接告诉 Claude AI（在项目里输入描述即可） |

---

## 常见问题

**Q：我已经收到了文件，放好了，然后呢？**

在项目目录里，输入 `/everything`，然后告诉 AI 你想要什么功能，它会自动检查环境并开始工作。

**Q：demo 和独立部署有什么区别？**

| | demo 槽位 | 独立部署 |
|---|---|---|
| 域名 | `demo.premom.tech`（共享） | `你的名字.premom.tech` |
| 共用 | 是，会被覆盖 | 否，专属 |
| 配置工作 | 零配置 | 需要 AI 部门加域名 |
| 适合 | 功能演示、快速验证 | 正式上线、长期运行 |

**Q：如果我不小心把 `ai-team-key` 提交到 git 了怎么办？**

立即联系 AI 部门，他们会：1）撤销旧密钥 2）生成新密钥 3）帮你从 git 历史中清除记录。

**Q：我不知道自己的项目需不需要 AI 功能怎么办？**

启动项目，在里面告诉 Claude："我的需求是 XXX，需要用到 AI 功能吗？" 它会告诉你。

---

## AI 部门交付标准格式（供 AI 部门参考）

> 本节是给 AI 部门的操作说明。非技术用户无需阅读，直接把本文档发给 AI 部门即可。

当非技术用户请求资源时，AI 部门统一打包成一个目录交付，命名为 `ai-team-file`。Claude AI 会自动识别并解析这个目录，无需用户手动操作。

### 标准目录结构

```
ai-team-file/
├── ai-team-key          # SSH 私钥（必须，无扩展名）
├── .env.docker.prod     # 生产环境配置（必须）
└── deploy-config.md     # 部署配置（可选，独立域名时必须）
```

### 各文件说明

**`ai-team-key`**（必须）
- 内容：EC2 服务器的 SSH 私钥
- 权限：交付后 Claude 会自动执行 `chmod 600`
- 注意：文件名必须是 `ai-team-key`，没有扩展名

**`.env.docker.prod`**（必须）
- 基于项目根目录的 `.env.docker.example` 填写
- 必填字段：

```env
POSTGRES_PASSWORD=<随机强密码，至少16位>
SECRET_KEY=<随机字符串，至少32位>
ANTHROPIC_API_KEY=<sk-ant-...，如项目有AI功能>
```

**`deploy-config.md`**（独立域名时必须，demo 槽位可不提供）
- 格式固定，Claude 会自动解析：

```markdown
# 部署配置

project_name: <项目英文名，小写连字符，如 customer-portal>
domain: <完整域名，如 customer-portal.premom.tech>
frontend_port: <前端端口，如 9701>
backend_port: <后端端口，如 8007>
```

### 交付方式

把整个 `ai-team-file` 目录压缩后通过安全渠道（企业内网盘、加密邮件等）发给用户。用户收到后解压，把路径告诉 Claude：

```
ai 部门提供的配置：/Users/xxx/Downloads/ai-team-file
```

Claude 会自动完成剩余操作。

### nginx 配置（独立部署时，需在 EC2 上操作）

在 `/opt/gateway/nginx/conf.d/` 创建配置文件，文件名为 `<domain>.conf`：

```nginx
server {
    listen 80;
    server_name <domain>;
    location / {
        proxy_pass http://172.17.0.1:<frontend_port>;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

执行 `sudo nginx -s reload` 后，把 `deploy-config.md` 放入 `ai-team-file` 目录交付用户。
