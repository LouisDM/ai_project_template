#!/usr/bin/env python3
"""
AI Project Template 一键部署脚本 — SSH 直连 EC2（无跳板机）

依赖: pip install paramiko

首次使用:
  1. 向团队管理员获取 ai-team-key 私钥，放到 D:\\ssh\\ai-team-key
     或通过环境变量 AI_TEAM_SSH_KEY 指定其他路径
  2. 按 CLAUDE.md 里的清单把下面几个常量改成你的项目名/端口

用法:
  python deploy.py            # 完整部署
  python deploy.py -y         # 跳过确认
  python deploy.py --check-only  # 仅检查服务器状态
"""
import os
import sys
import time
import tarfile
import tempfile
import argparse
from pathlib import Path

import paramiko

# ── 项目配置 ────────────────────────────────────────────
# 默认发布到共享的 demo 测试环境：
#   - 域名:   https://demo.premom.tech/（已配好 nginx + 泛域名证书）
#   - 端口:   9700 前端 / 8006 后端
#   - 容器名: demo-frontend / demo-backend / demo-postgres
#
# 想部署到独立环境时，把下面几个常量改成自己项目的值：
#   PROJECT_NAME  → 唯一标识（影响容器名、部署目录、docker 网络名）
#   PUBLIC_DOMAIN → 你自己的域名（需在 DNS 先指向 EC2 公网 IP）
#   FRONTEND_PORT / BACKEND_PORT → 在服务器上不冲突的端口
# 改完以后记得同步改 docker-compose.prod.yml 里的 container_name 和 ports。
PROJECT_NAME = "demo"                     # 容器名前缀、部署目录名、docker 网络名
PUBLIC_DOMAIN = "demo.premom.tech"        # 对外域名（gateway-nginx 会做 HTTPS 反代）
EC2_HOST = "cms.premom.tech"              # EC2 SSH 目标
EC2_USER = "ec2-user"

# SSH 私钥查找顺序：环境变量 → 项目本地 ssh/ 目录 → 全局 D:\ssh\
_PROJECT_SSH_KEY = str(Path(__file__).resolve().parent / "ssh" / "ai-team-key")
SSH_KEY_PATH = (
    os.environ.get("AI_TEAM_SSH_KEY")
    or (_PROJECT_SSH_KEY if os.path.exists(_PROJECT_SSH_KEY) else r"D:\ssh\ai-team-key")
)

FRONTEND_PORT = 9700
BACKEND_PORT = 8006

DEPLOY_DIR = f"/home/ec2-user/{PROJECT_NAME}"
PROJECT_DIR = Path(__file__).resolve().parent
ARCHIVE_NAME = f"{PROJECT_NAME}-deploy.tar.gz"
DOCKER_NETWORK = f"{PROJECT_NAME}_net"    # 对应 docker-compose.prod.yml 里 networks.default.name

# 打包时排除
EXCLUDES = {
    "node_modules", ".next", ".venv", "venv", "__pycache__", ".git",
    "test-results", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "output", ".env.docker", "deploy.py", "deploy.sh", "dist",
    "test.db", "uploads",
}


def log(msg: str):
    try:
        print(f"  {msg}")
    except UnicodeEncodeError:
        print(f"  {msg.encode('ascii', 'replace').decode()}")


def create_archive() -> str:
    archive_path = os.path.join(tempfile.gettempdir(), ARCHIVE_NAME)
    print("\n[1/4] 打包项目文件...")

    def tar_filter(tarinfo):
        parts = Path(tarinfo.name).parts
        for part in parts:
            if part in EXCLUDES:
                return None
            if part.endswith(".pyc"):
                return None
        return tarinfo

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(str(PROJECT_DIR), arcname=PROJECT_NAME, filter=tar_filter)

    size_mb = os.path.getsize(archive_path) / (1024 * 1024)
    log(f"打包完成: {size_mb:.1f} MB -> {archive_path}")
    return archive_path


def _set_keepalive(client: paramiko.SSHClient, interval: int = 15) -> None:
    transport = client.get_transport()
    if transport:
        transport.set_keepalive(interval)


def connect_ec2() -> paramiko.SSHClient:
    if not os.path.exists(SSH_KEY_PATH):
        print(f"[错误] SSH 私钥未找到: {SSH_KEY_PATH}")
        print("请向团队管理员获取 ai-team-key，放到以下任一位置：")
        print(f"  1. 项目本地（推荐）:  {_PROJECT_SSH_KEY}")
        print("  2. 全局:              D:\\ssh\\ai-team-key")
        print("  3. 环境变量:          AI_TEAM_SSH_KEY=<你的路径>")
        print("注意：项目本地 ssh/ 目录已在 .gitignore 中忽略，不会提交。")
        sys.exit(1)

    ec2 = paramiko.SSHClient()
    ec2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ec2.connect(
        EC2_HOST,
        username=EC2_USER,
        key_filename=SSH_KEY_PATH,
        timeout=15,
        look_for_keys=False,
        allow_agent=False,
    )
    _set_keepalive(ec2)
    return ec2


def run_remote(client: paramiko.SSHClient, cmd: str, label: str = "") -> str:
    if label:
        log(f"{label}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=600)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out.strip():
        for line in out.strip().split("\n"):
            log(f"  {line}")
    if exit_code != 0 and err.strip():
        for line in err.strip().split("\n"):
            log(f"  [stderr] {line}")
    return out


def check_environment(ec2: paramiko.SSHClient):
    print("\n[检查] EC2 服务器环境")
    print("-" * 50)
    run_remote(ec2, "echo '=== OS ===' && cat /etc/os-release | head -3", "操作系统:")
    run_remote(ec2, "echo '=== Docker ===' && docker --version 2>&1 && docker compose version 2>&1", "Docker:")
    run_remote(ec2, "echo '=== Disk ===' && df -h /home/ec2-user", "磁盘空间:")
    run_remote(ec2, "echo '=== Memory ===' && free -h", "内存:")
    run_remote(
        ec2,
        f"echo '=== Ports ===' && sudo ss -tlnp 2>/dev/null | grep -E ':({FRONTEND_PORT}|{BACKEND_PORT}) ' || echo '  无占用'",
        f"端口占用 ({FRONTEND_PORT}/{BACKEND_PORT}):"
    )
    print("-" * 50)


def upload_to_ec2(ec2: paramiko.SSHClient, archive_path: str):
    print("\n[2/4] 上传到 EC2...")
    sftp = ec2.open_sftp()
    remote_path = f"/home/ec2-user/{ARCHIVE_NAME}"
    sftp.put(archive_path, remote_path, callback=lambda sent, total: None)
    sftp.close()
    log("上传完成")


def deploy_on_ec2(ec2: paramiko.SSHClient):
    print("\n[3/4] 在 EC2 上解压并启动...")

    run_remote(ec2,
        f"cd /home/ec2-user && tar xzf {ARCHIVE_NAME} && rm -f {ARCHIVE_NAME}",
        "解压文件..."
    )

    run_remote(ec2,
        f"cd {DEPLOY_DIR} && cp .env.docker.prod .env.docker",
        "配置生产环境..."
    )

    run_remote(ec2,
        "groups | grep -q docker || sudo usermod -aG docker ec2-user",
        "检查 Docker 权限..."
    )

    print("\n    构建并启动 Docker 服务（这需要几分钟）...")
    run_remote(ec2,
        f"cd {DEPLOY_DIR} && sudo docker compose -f docker-compose.prod.yml up -d --build 2>&1 | tail -30",
        "Docker 构建中..."
    )

    log("等待服务启动 (15s)...")
    time.sleep(15)

    # 让 gateway-nginx 能通过容器名访问 frontend（一次性，幂等）
    run_remote(ec2,
        f"sudo docker network connect {DOCKER_NETWORK} gateway-nginx 2>&1 | grep -v 'already exists' || true",
        f"连接 gateway-nginx 到 {DOCKER_NETWORK}..."
    )

    run_remote(ec2,
        f"cd {DEPLOY_DIR} && sudo docker compose -f docker-compose.prod.yml ps",
        "服务状态:"
    )


def verify(ec2: paramiko.SSHClient):
    print("\n[4/4] 验证部署...")
    run_remote(ec2, f"curl -sf http://localhost:{BACKEND_PORT}/health 2>&1 || echo 'Backend health check failed'", "后端健康检查:")
    run_remote(ec2, f"curl -sf -o /dev/null -w '%{{http_code}}' http://localhost:{FRONTEND_PORT} 2>&1 || echo 'Frontend check failed'", "前端状态码:")


def main():
    parser = argparse.ArgumentParser(description=f"{PROJECT_NAME} 部署脚本")
    parser.add_argument("--check-only", action="store_true", help="仅检查 EC2 环境")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认直接部署")
    args = parser.parse_args()

    print("=" * 50)
    print(f"  {PROJECT_NAME} 自动化部署")
    print("=" * 50)

    print(f"\n连接 EC2 ({EC2_HOST})...")
    ec2 = connect_ec2()
    log("EC2 连接成功")

    check_environment(ec2)

    if args.check_only:
        print("\n[OK] 环境检查完成（--check-only 模式）")
        ec2.close()
        return

    if not args.yes:
        answer = input("\n环境检查完毕，是否继续部署？(y/N): ").strip().lower()
        if answer != "y":
            print("已取消")
            ec2.close()
            return

    archive_path = create_archive()
    upload_to_ec2(ec2, archive_path)
    deploy_on_ec2(ec2)
    verify(ec2)

    os.remove(archive_path)
    ec2.close()

    print("\n" + "=" * 50)
    print("  部署完成!")
    print(f"  域名（HTTPS）: https://{PUBLIC_DOMAIN}/")
    print(f"  前端直连:     http://{EC2_HOST}:{FRONTEND_PORT}")
    print(f"  后端直连:     http://{EC2_HOST}:{BACKEND_PORT}")
    print(f"  健康检查:     http://{EC2_HOST}:{BACKEND_PORT}/health")
    print("=" * 50)


if __name__ == "__main__":
    main()
