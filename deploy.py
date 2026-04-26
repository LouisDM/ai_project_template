#!/usr/bin/env python3
"""
AI Project Template 一键部署脚本 — 支持多项目动态端口分配 + 二级域名

每个项目自动分配独立的前端端口和二级域名：
  - 端口范围: 22222-22333（仅前端需要暴露，后端通过 Docker 内部网络访问）
  - 域名格式: <项目名>.demo.intelliastra.com

依赖: pip install paramiko

用法:
  python deploy.py            # 完整部署（自动分配端口）
  python deploy.py -y         # 跳过确认
  python deploy.py --check-only  # 仅检查服务器状态
  python deploy.py --port 22222  # 指定前端端口
  python deploy.py --domain myapp.demo.intelliastra.com  # 指定域名
"""
import os
import sys
import time
import tarfile
import tempfile
import argparse
import re
from pathlib import Path

import paramiko

# ── 服务器配置 ────────────────────────────────────────────
EC2_HOST = "47.121.130.229"
EC2_USER = "root"
SSH_PASSWORD = os.environ.get("SSH_PASSWORD", "P6ZxidTmtks!qPC")

# ── 端口配置 ────────────────────────────────────────────
PORT_RANGE_START = 22222
PORT_RANGE_END = 22333
NGINX_CONF_DIR = "/www/server/panel/vhost/nginx"
DOMAIN_SUFFIX = "demo.intelliastra.com"

# ── 项目配置 ────────────────────────────────────────────
PROJECT_NAME = "demo"
PUBLIC_DOMAIN = None
FRONTEND_PORT = None

DEPLOY_DIR = f"/root/{PROJECT_NAME}"
PROJECT_DIR = Path(__file__).resolve().parent
ARCHIVE_NAME = f"{PROJECT_NAME}-deploy.tar.gz"

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


def sanitize_domain_name(name: str) -> str:
    sanitized = re.sub(r'[^a-zA-Z0-9-]', '-', name.lower())
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')
    return sanitized


def get_next_available_port(ec2: paramiko.SSHClient) -> int:
    stdin, stdout, stderr = ec2.exec_command(
        f"ss -tln 2>/dev/null | awk '{{print $4}}' | grep -oE '[0-9]+$' | sort -n | uniq"
    )
    used_ports = set()
    for line in stdout.read().decode().strip().split('\n'):
        if line.strip().isdigit():
            used_ports.add(int(line.strip()))

    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        if port not in used_ports:
            return port

    raise RuntimeError(f"端口范围 {PORT_RANGE_START}-{PORT_RANGE_END} 已耗尽")


def generate_nginx_config(project_name: str, domain: str, frontend_port: int) -> str:
    """生成 nginx 反向代理配置 — 所有请求都走前端容器，前端 nginx 再反代 /api/ 到后端"""
    return f"""# Auto-generated for {project_name}
server {{
    listen 80;
    server_name {domain};

    client_max_body_size 100M;

    location / {{
        proxy_pass http://127.0.0.1:{frontend_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
}}
"""


def create_archive() -> str:
    archive_path = os.path.join(tempfile.gettempdir(), ARCHIVE_NAME)
    print("\n[1/5] 打包项目文件...")

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
    log(f"打包完成: {size_mb:.1f} MB")
    return archive_path


def connect_ec2() -> paramiko.SSHClient:
    ec2 = paramiko.SSHClient()
    ec2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ec2.connect(
        EC2_HOST, username=EC2_USER, password=SSH_PASSWORD,
        timeout=15, look_for_keys=False, allow_agent=False,
    )
    transport = ec2.get_transport()
    if transport:
        transport.set_keepalive(15)
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


def check_environment(ec2: paramiko.SSHClient, frontend_port: int):
    print("\n[检查] EC2 服务器环境")
    print("-" * 50)
    run_remote(ec2, "cat /etc/os-release | head -3", "操作系统:")
    run_remote(ec2, "docker --version 2>&1 && docker compose version 2>&1", "Docker:")
    run_remote(ec2, "df -h /root", "磁盘空间:")
    run_remote(ec2, "free -h", "内存:")
    run_remote(
        ec2,
        f"ss -tlnp 2>/dev/null | grep -E ':{frontend_port} ' || echo '  端口 {frontend_port} 未被占用 ✓'",
        f"端口检查:"
    )
    print("-" * 50)


def upload_to_ec2(ec2: paramiko.SSHClient, archive_path: str):
    print("\n[2/5] 上传到 EC2...")
    sftp = ec2.open_sftp()
    sftp.put(archive_path, f"/root/{ARCHIVE_NAME}")
    sftp.close()
    log("上传完成")


def deploy_on_ec2(ec2: paramiko.SSHClient, frontend_port: int):
    print("\n[3/5] 在 EC2 上解压并启动...")

    run_remote(ec2,
        f"mkdir -p {DEPLOY_DIR} && cd /root && tar xzf {ARCHIVE_NAME} && rm -f {ARCHIVE_NAME}",
        "解压文件..."
    )

    run_remote(ec2, f"cd {DEPLOY_DIR} && cp .env.docker.prod .env.docker", "配置生产环境...")
    run_remote(ec2, f"groups | grep -q docker || sudo usermod -aG docker {EC2_USER}", "检查 Docker 权限...")

    # 写入前端端口到 .env.docker
    run_remote(ec2,
        f"cd {DEPLOY_DIR} && echo 'FRONTEND_PORT={frontend_port}' >> .env.docker",
        "写入端口配置..."
    )

    print("\n    构建并启动 Docker 服务（这需要几分钟）...")
    run_remote(ec2,
        f"cd {DEPLOY_DIR} && sudo docker compose -f docker-compose.prod.yml up -d --build 2>&1 | tail -30",
        "Docker 构建中..."
    )

    log("等待服务启动 (15s)...")
    time.sleep(15)

    run_remote(ec2,
        f"cd {DEPLOY_DIR} && sudo docker compose -f docker-compose.prod.yml ps",
        "服务状态:"
    )


def setup_nginx(ec2: paramiko.SSHClient, domain: str, frontend_port: int):
    print("\n[4/5] 配置 nginx 反向代理...")

    config_content = generate_nginx_config(PROJECT_NAME, domain, frontend_port)
    config_path = f"{NGINX_CONF_DIR}/{PROJECT_NAME}.conf"

    # 使用 heredoc 写入配置文件，避免引号转义问题
    run_remote(ec2, f"cat > {config_path} << 'NGINX_EOF'\n{config_content}NGINX_EOF", "生成 nginx 配置...")

    run_remote(ec2, "/www/server/nginx/sbin/nginx -t 2>&1", "测试 nginx 配置...")
    run_remote(ec2, "/www/server/nginx/sbin/nginx -s reload 2>&1", "重载 nginx...")

    log(f"域名配置完成: http://{domain}")


def verify(ec2: paramiko.SSHClient, domain: str, frontend_port: int):
    print("\n[5/5] 验证部署...")

    run_remote(ec2,
        f"curl -sf -o /dev/null -w '%{{http_code}}' http://{domain}/ 2>&1 || echo '域名访问失败'",
        f"域名检查 ({domain}):"
    )
    run_remote(ec2,
        f"curl -sf -o /dev/null -w '%{{http_code}}' http://localhost:{frontend_port}/ 2>&1 || echo '端口访问失败'",
        f"端口检查 ({frontend_port}):"
    )
    run_remote(ec2,
        f"curl -sf -o /dev/null -w '%{{http_code}}' http://localhost:{frontend_port}/health 2>&1 || echo 'API 检查失败'",
        "API 健康检查:"
    )


def main():
    global PROJECT_NAME, PUBLIC_DOMAIN, FRONTEND_PORT, DEPLOY_DIR, ARCHIVE_NAME

    parser = argparse.ArgumentParser(description="AI Project 自动化部署")
    parser.add_argument("--check-only", action="store_true", help="仅检查 EC2 环境")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument("--port", type=int, default=None, help=f"指定端口（{PORT_RANGE_START}-{PORT_RANGE_END}）")
    parser.add_argument("--domain", type=str, default=None, help="指定二级域名")
    parser.add_argument("--name", type=str, default=None, help="指定项目名")
    args = parser.parse_args()

    if args.name:
        PROJECT_NAME = args.name
        DEPLOY_DIR = f"/root/{PROJECT_NAME}"
        ARCHIVE_NAME = f"{PROJECT_NAME}-deploy.tar.gz"

    print("=" * 60)
    print(f"  {PROJECT_NAME} 自动化部署")
    print("=" * 60)

    print(f"\n连接 EC2 ({EC2_HOST})...")
    ec2 = connect_ec2()
    log("EC2 连接成功")

    # 分配端口
    if args.port:
        FRONTEND_PORT = args.port
        log(f"使用指定端口: {FRONTEND_PORT}")
    else:
        FRONTEND_PORT = get_next_available_port(ec2)
        log(f"自动分配端口: {FRONTEND_PORT}")

    # 分配域名
    if args.domain:
        PUBLIC_DOMAIN = args.domain
    else:
        PUBLIC_DOMAIN = f"{sanitize_domain_name(PROJECT_NAME)}.{DOMAIN_SUFFIX}"
    log(f"分配域名: {PUBLIC_DOMAIN}")

    check_environment(ec2, FRONTEND_PORT)

    if args.check_only:
        print("\n[OK] 环境检查完成")
        ec2.close()
        return

    if not args.yes:
        print(f"\n部署配置:")
        print(f"  项目名: {PROJECT_NAME}")
        print(f"  域名:   http://{PUBLIC_DOMAIN}")
        print(f"  前端端口: {FRONTEND_PORT}")
        answer = input("\n确认部署？(y/N): ").strip().lower()
        if answer != "y":
            print("已取消")
            ec2.close()
            return

    archive_path = create_archive()
    upload_to_ec2(ec2, archive_path)
    deploy_on_ec2(ec2, FRONTEND_PORT)
    setup_nginx(ec2, PUBLIC_DOMAIN, FRONTEND_PORT)
    verify(ec2, PUBLIC_DOMAIN, FRONTEND_PORT)

    os.remove(archive_path)
    ec2.close()

    print("\n" + "=" * 60)
    print("  部署完成!")
    print(f"  域名入口: http://{PUBLIC_DOMAIN}/")
    print(f"  前端直连: http://{EC2_HOST}:{FRONTEND_PORT}")
    print(f"  API 检查: http://{PUBLIC_DOMAIN}/health")
    print("=" * 60)


if __name__ == "__main__":
    main()
