#!/bin/bash
# Docker配置测试脚本

set -e

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[测试] $1${NC}"
}

error() {
    echo -e "${RED}[错误] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[警告] $1${NC}"
}

log "开始Docker配置测试..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    error "Docker未安装，请先安装Docker"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    error "Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

log "Docker环境检查通过"

# 检查必要文件
required_files=(
    "Dockerfile"
    "docker-compose.yml"
    "docker-manage.sh"
    "docker-start.sh"
    "requirements.txt"
    "web_server.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        error "缺少必要文件: $file"
        exit 1
    fi
    log "✓ $file 存在"
done

# 检查Dockerfile语法
log "检查Dockerfile语法..."
if docker build --dry-run . > /dev/null 2>&1; then
    log "✓ Dockerfile语法正确"
else
    error "Dockerfile语法错误"
    exit 1
fi

# 检查docker-compose.yml语法
log "检查docker-compose.yml语法..."
if docker compose config > /dev/null 2>&1; then
    log "✓ docker-compose.yml语法正确"
else
    error "docker-compose.yml语法错误"
    exit 1
fi

# 检查脚本权限
scripts=("docker-manage.sh" "docker-start.sh")
for script in "${scripts[@]}"; do
    if [ -x "$script" ]; then
        log "✓ $script 有执行权限"
    else
        warn "$script 没有执行权限，正在修复..."
        chmod +x "$script"
        log "✓ $script 权限已修复"
    fi
done

log "所有测试通过！Docker配置正确。"
log ""
log "可以使用以下命令启动服务："
log "  ./docker-start.sh          # 快速启动"
log "  ./docker-manage.sh start-web  # 启动Web服务"
log "  ./docker-manage.sh update     # 更新数据"
