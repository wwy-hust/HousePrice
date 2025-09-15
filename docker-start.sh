#!/bin/bash
# 房价数据可视化系统 Docker 快速启动脚本

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "错误: Docker未运行"
    exit 1
fi

log "开始启动房价数据可视化系统..."

# 构建并启动服务
log "构建Docker镜像..."
docker compose build

log "启动Web服务..."
docker compose up -d house-price-web

# 等待服务启动
log "等待服务启动..."
sleep 10

# 检查服务状态
if docker compose ps house-price-web | grep -q "Up"; then
    log "✅ 服务启动成功！"
    log "🌐 访问地址: http://localhost:8000"
    log "📊 房价数据可视化系统已就绪"
    echo ""
    log "常用命令:"
    echo "  查看状态: docker compose ps"
    echo "  查看日志: docker compose logs -f house-price-web"
    echo "  停止服务: docker compose down"
    echo "  数据采集: docker compose run --rm house-price-collector"
    echo "  数据处理: docker compose run --rm house-price-processor"
else
    warn "❌ 服务启动失败"
    echo "查看错误日志:"
    docker compose logs house-price-web
    exit 1
fi
