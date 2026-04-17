# SSH 密钥目录

把 `ai-team-key` 私钥放到这个目录下（本目录已在 `.gitignore` 忽略）：

```
ssh/
├── README.md         (本文件，可提交)
└── ai-team-key       (私钥，不要提交)
```

## 获取密钥

向团队管理员索取 `ai-team-key`，它是登录 EC2 `cms.premom.tech` 的 Ed25519 私钥。

## 放置路径

`deploy.py` 按以下优先级查找：

1. 环境变量 `AI_TEAM_SSH_KEY`
2. 本目录 `./ssh/ai-team-key`（推荐）
3. `D:\ssh\ai-team-key`（旧全局位置）

## 权限（Windows 不强制，Linux/Mac 必须）

```bash
chmod 600 ssh/ai-team-key
```
