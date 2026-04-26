#!/usr/bin/env python3
"""
AI Project Template 一键部署脚本 — 支持多项目动态端口分配 + 二级域名

每个项目自动分配独立的端口对（前端/后端）和二级域名：
  - 端口范围: 22222-22333（前端），对应后端端口 +1
  - 域名格式: <项目名>.demo.intelliastra.com

依赖: pip install paramiko

用法:
  python deploy.py            # 完整部署（自动分配端口）
  python deploy.py -y         # 跳过确认
  python deploy.py --check-only  # 仅检查服务器状态
  python deploy.py --port 22222  # 指定前端端口（后端自动用 22223）
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
NGINX_CONF_DIR = "/etc/nginx/conf.d"
DOMAIN_SUFFIX = "demo.intelliastra.com"

# ── 项目配置 ────────────────────────────────────────────
# 默认发布到共享的 demo 测试环境：
# 如需独立部署，修改 PROJECT_NAME 即可，端口和域名会自动分配
PROJECT_NAME = "demo"                     # 容器名前缀、部署目录名
PUBLIC_DOMAIN = None                      # 自动分配: {PROJECT_NAME}.{DOMAIN_SUFFIX}

FRONTEND_PORT = None                      # 自动分配
BACKEND_PORT = None                       # 自动分配: FRONTEND_PORT + 1

DEPLOY_DIR = f"/root/{PROJECT_NAME}"
PROJECT_DIR = Path(__file__).resolve().parent
ARCHIVE_NAME = f"{PROJECT_NAME}-deploy.tar.gz"

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


def sanitize_domain_name(name: str) -> str:
    """将项目名转换为合法的域名前缀（小写、替换非法字符）"""
    sanitized = re.sub(r'[^a-zA-Z0-9-]', '-', name.lower())
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')
    return sanitized


def get_next_available_ports(ec2: paramiko.SSHClient) -> tuple[int, int]:
    """扫描端口范围，返回下一个可用的前端/后端端口对"""
    stdin, stdout, stderr = ec2.exec_command(
        f"ss -tln 2>/dev/null | awk '{{print $4}}' | grep -oE '[0-9]+$' | sort -n | uniq"
    )
    used_ports = set()
    for line in stdout.read().decode().strip().split('\n'):
        if line.strip().isdigit():
            used_ports.add(int(line.strip()))

    for port in range(PORT_RANGE_START, PORT_RANGE_END, 2):
        backend_port = port + 1
        if port not in used_ports and backend_port not in used_ports:
            return port, backend_port

    raise RuntimeError(f"端口范围 {PORT_RANGE_START}-{PORT_RANGE_END} 已耗尽，无法分配新端口")


def generate_nginx_config(project_name: str, domain: str, frontend_port: int, backend_port: int) -> str:
    """生成 nginx 反向代理配置"""
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

    location /api/ {{
        proxy_pass http://127.0.0.1:{backend_port}/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location /uploads/ {{
        proxy_pass http://127.0.0.1:{backend_port}/uploads/;
        proxy_set_header Host $host;
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
    log(f"打包完成: {size_mb:.1f} MB -> {archive_path}")
    return archive_path


def _set_keepalive(client: paramiko.SSHClient, interval: int = 15) -> None:
    transport = client.get_transport()
    if transport:
        transport.set_keepalive(interval)


def connect_ec2() -> paramiko.SSHClient:
    ec2 = paramiko.SSHClient()
    ec2.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ec2.connect(
        EC2_HOST,
        username=EC2_USER,
        password=SSH_PASSWORD,
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


def check_environment(ec2: paramiko.SSHClient, frontend_port: int, backend_port: int):
    print("\n[检查] EC2 服务器环境")
    print("-" * 50)
    run_remote(ec2, "echo '=== OS ===' && cat /etc/os-release | head -3", "操作系统:")
    run_remote(ec2, "echo '=== Docker ===' && docker --version 2>&1 && docker compose version 2>&1", "Docker:")
    run_remote(ec2, "echo '=== Disk ===' && df -h /root", "磁盘空间:")
    run_remote(ec2, "echo '=== Memory ===' && free -h", "内存:")
    run_remote(
        ec2,
        f"echo '=== Ports ===' && sudo ss -tlnp 2>/dev/null | grep -E ':({frontend_port}|{backend_port}) ' || echo '  端口未被占用 ✓'",
        f"端口占用 ({frontend_port}/{backend_port}):"
    )
    print("-" * 50)


def upload_to_ec2(ec2: paramiko.SSHClient, archive_path: str):
    print("\n[2/5] 上传到 EC2...")
    sftp = ec2.open_sftp()
    remote_path = f"/root/{ARCHIVE_NAME}"
    sftp.put(archive_path, remote_path, callback=lambda sent, total: None)
    sftp.close()
    log("上传完成")


def deploy_on_ec2(ec2: paramiko.SSHClient, frontend_port: int, backend_port: int):
    print("\n[3/5] 在 EC2 上解压并启动...")

    run_remote(ec2,
        f"mkdir -p {DEPLOY_DIR} && cd /root && tar xzf {ARCHIVE_NAME} && rm -f {ARCHIVE_NAME}",
        "解压文件..."
    )

    run_remote(ec2,
        f"cd {DEPLOY_DIR} && cp .env.docker.prod .env.docker",
        "配置生产环境..."
    )

    run_remote(ec2,
        f"groups | grep -q docker || sudo usermod -aG docker {EC2_USER}",
        "检查 Docker 权限..."
    )

    # 写入端口环境变量到 .env.docker
    run_remote(ec2,
        f"cd {DEPLOY_DIR} && echo 'FRONTEND_PORT={frontend_port}' >> .env.docker && echo 'BACKEND_PORT={backend_port}' >> .env.docker",
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


def setup_nginx(ec2: paramiko.SSHClient, domain: str, frontend_port: int, backend_port: int):
    print("\n[4/5] 配置 nginx 反向代理...")

    config_content = generate_nginx_config(PROJECT_NAME, domain, frontend_port, backend_port)
    config_path = f"{NGINX_CONF_DIR}/{PROJECT_NAME}.conf"

    # 写入配置文件
    run_remote(ec2, f"cat > {config_path} << 'EOF'\n{config_content}EOF", "生成 nginx 配置...")

    # 测试并重载 nginx
    run_remote(ec2, "nginx -t 2>&1", "测试 nginx 配置...")
    run_remote(ec2, "nginx -s reload 2>&1 || nginx 2>&1", "重载 nginx...")

    log(f"域名配置完成: http://{domain}")


def verify(ec2: paramiko.SSHClient, domain: str, frontend_port: int):
    print("\n[5/5] 验证部署...")

    # 通过 nginx 域名检查
    run_remote(ec2, f"curl -sf -o /dev/null -w '%{{http_code}}' http://{domain}/ 2>&1 || echo '域名访问失败'", f"域名检查 ({domain}):")

    # 通过本地端口检查
    run_remote(ec2, f"curl -sf -o /dev/null -w '%{{http_code}}' http://localhost:{frontend_port}/ 2>&1 || echo '端口访问失败'", f"端口检查 ({frontend_port}):")

    # 检查 API
    run_remote(ec2, f"curl -sf -o /dev/null -w '%{{http_code}}' http://localhost:{frontend_port}/api/health 2>&1 || echo 'API 检查失败'", "API 健康检查:")


def main():
    global PROJECT_NAME, PUBLIC_DOMAIN, FRONTEND_PORT, BACKEND_PORT, DEPLOY_DIR, ARCHIVE_NAME

    parser = argparse.ArgumentParser(description=f"AI Project 自动化部署 — 支持多项目动态端口")
    parser.add_argument("--check-only", action="store_true", help="仅检查 EC2 环境")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认直接部署")
    parser.add_argument("--port", type=int, default=None, help=f"指定前端端口（范围: {PORT_RANGE_START}-{PORT_RANGE_END}）")
    parser.add_argument("--domain", type=str, default=None, help="指定二级域名（如 myapp.demo.intelliastra.com）")
    parser.add_argument("--name", type=str, default=None, help="指定项目名（影响容器名和部署目录）")
    args = parser.parse_args()

    # 覆盖项目名
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
        BACKEND_PORT = args.port + 1
        log(f"使用指定端口: 前端={FRONTEND_PORT}, 后端={BACKEND_PORT}")
    else:
        FRONTEND_PORT, BACKEND_PORT = get_next_available_ports(ec2)
        log(f"自动分配端口: 前端={FRONTEND_PORT}, 后端={BACKEND_PORT}")

    # 分配域名
    if args.domain:
        PUBLIC_DOMAIN = args.domain
    else:
        domain_prefix = sanitize_domain_name(PROJECT_NAME)
        PUBLIC_DOMAIN = f"{domain_prefix}.{DOMAIN_SUFFIX}"
    log(f"分配域名: {PUBLIC_DOMAIN}")

    check_environment(ec2, FRONTEND_PORT, BACKEND_PORT)

    if args.check_only:
        print("\n[OK] 环境检查完成（--check-only 模式）")
        ec2.close()
        return

    if not args.yes:
        print(f"\n部署配置:")
        print(f"  项目名: {PROJECT_NAME}")
        print(f"  域名:   http://{PUBLIC_DOMAIN}")
        print(f"  前端端口: {FRONTEND_PORT}")
        print(f"  后端端口: {BACKEND_PORT}")
        answer = input("\n确认部署？(y/N): ").strip().lower()
        if answer != "y":
            print("已取消")
            ec2.close()
            return

    archive_path = create_archive()
    upload_to_ec2(ec2, archive_path)
    deploy_on_ec2(ec2, FRONTEND_PORT, BACKEND_PORT)
    setup_nginx(ec2, PUBLIC_DOMAIN, FRONTEND_PORT, BACKEND_PORT)
    verify(ec2, PUBLIC_DOMAIN, FRONTEND_PORT)

    os.remove(archive_path)
    ec2.close()

    print("\n" + "=" * 60)
    print("  部署完成!")
    print(f"  域名入口:     http://{PUBLIC_DOMAIN}/")
    print(f"  前端直连:     http://{EC2_HOST}:{FRONTEND_PORT}")
    print(f"  后端直连:     http://{EC2_HOST}:{BACKEND_PORT}")
    print(f"  健康检查:     http://{PUBLIC_DOMAIN}/api/health")
    print("=" * 60)


if __name__ == "__main__":
    main()
