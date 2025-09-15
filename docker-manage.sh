#!/bin/bash
# 房价数据可视化系统 Docker 管理脚本

set -e

# 配置变量
PROJECT_NAME="house-price"
COMPOSE_FILE="docker-compose.yml"
WEB_SERVICE="house-price-web"
COLLECTOR_SERVICE="house-price-collector"
PROCESSOR_SERVICE="house-price-processor"
BATCH_SERVICE="house-price-batch"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# 检查Docker和Docker Compose
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker未安装，请先安装Docker"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi

    # 检查Docker是否运行
    if ! docker info &> /dev/null; then
        error "Docker未运行，请启动Docker服务"
        exit 1
    fi

    log "Docker环境检查通过"
}

# 检查项目文件
check_project() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "docker-compose.yml文件不存在"
        exit 1
    fi

    if [ ! -f "Dockerfile" ]; then
        error "Dockerfile文件不存在"
        exit 1
    fi

    if [ ! -f "requirements.txt" ]; then
        error "requirements.txt文件不存在"
        exit 1
    fi

    log "项目文件检查通过"
}

# 构建镜像
build_images() {
    log "构建Docker镜像..."
    docker compose build --no-cache
    log "镜像构建完成"
}

# 启动Web服务
start_web() {
    log "启动房价数据可视化Web服务..."
    docker compose up -d $WEB_SERVICE
    
    # 等待服务启动
    sleep 5
    
    if docker compose ps $WEB_SERVICE | grep -q "Up"; then
        log "Web服务启动成功"
        log "访问地址: http://localhost:8000"
        return 0
    else
        error "Web服务启动失败"
        docker compose logs $WEB_SERVICE
        return 1
    fi
}

# 停止Web服务
stop_web() {
    log "停止Web服务..."
    docker compose stop $WEB_SERVICE
    log "Web服务已停止"
}

# 重启Web服务
restart_web() {
    log "重启Web服务..."
    docker compose restart $WEB_SERVICE
    log "Web服务已重启"
}

# 启动所有服务
start_all() {
    log "启动所有服务..."
    docker compose up -d
    log "所有服务启动完成"
}

# 停止所有服务
stop_all() {
    log "停止所有服务..."
    docker compose down
    log "所有服务已停止"
}

# 重启所有服务
restart_all() {
    log "重启所有服务..."
    docker compose restart
    log "所有服务已重启"
}

# 查看服务状态
status() {
    log "服务状态:"
    docker compose ps
    echo ""
    
    # 检查Web服务健康状态
    if docker compose ps $WEB_SERVICE | grep -q "Up"; then
        log "Web服务运行正常"
        info "访问地址: http://localhost:8000"
    else
        warn "Web服务未运行"
    fi
}

# 查看日志
logs() {
    local service=${1:-$WEB_SERVICE}
    log "查看 $service 服务日志..."
    docker compose logs -f $service
}

# 进入容器
exec_container() {
    local service=${1:-$WEB_SERVICE}
    log "进入 $service 容器..."
    docker compose exec $service /bin/bash
}

# 数据采集
collect_data() {
    log "开始数据采集..."
    docker compose run --rm $COLLECTOR_SERVICE
    log "数据采集完成"
}

# 数据处理
process_data() {
    log "开始数据处理..."
    docker compose run --rm $PROCESSOR_SERVICE
    log "数据处理完成"
}

# 批量处理
batch_process() {
    log "开始批量处理..."
    docker compose run --rm $BATCH_SERVICE
    log "批量处理完成"
}

# 完整数据更新流程
update_data() {
    log "开始完整数据更新流程..."
    
    # 1. 数据采集
    log "步骤1: 数据采集"
    collect_data
    
    # 2. 数据处理
    log "步骤2: 数据处理"
    process_data
    
    # 3. 批量处理
    log "步骤3: 批量处理"
    batch_process
    
    log "数据更新流程完成"
}

# 清理资源
cleanup() {
    log "清理Docker资源..."
    
    # 停止并删除容器
    docker compose down
    
    # 删除未使用的镜像
    docker image prune -f
    
    # 删除未使用的卷
    docker volume prune -f
    
    log "资源清理完成"
}

# 备份数据
backup_data() {
    local backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
    log "备份数据到 $backup_dir..."
    
    mkdir -p "$backup_dir"
    
    # 备份collected_data目录
    if [ -d "collected_data" ]; then
        cp -r collected_data "$backup_dir/"
        log "已备份 collected_data 目录"
    fi
    
    # 备份results目录
    if [ -d "results" ]; then
        cp -r results "$backup_dir/"
        log "已备份 results 目录"
    fi
    
    # 备份日志
    if [ -d "logs" ]; then
        cp -r logs "$backup_dir/"
        log "已备份 logs 目录"
    fi
    
    log "数据备份完成: $backup_dir"
}

# 恢复数据
restore_data() {
    local backup_dir=$1
    
    if [ -z "$backup_dir" ]; then
        error "请指定备份目录"
        exit 1
    fi
    
    if [ ! -d "$backup_dir" ]; then
        error "备份目录不存在: $backup_dir"
        exit 1
    fi
    
    log "从 $backup_dir 恢复数据..."
    
    # 恢复collected_data目录
    if [ -d "$backup_dir/collected_data" ]; then
        rm -rf collected_data
        cp -r "$backup_dir/collected_data" .
        log "已恢复 collected_data 目录"
    fi
    
    # 恢复results目录
    if [ -d "$backup_dir/results" ]; then
        rm -rf results
        cp -r "$backup_dir/results" .
        log "已恢复 results 目录"
    fi
    
    # 恢复日志
    if [ -d "$backup_dir/logs" ]; then
        rm -rf logs
        cp -r "$backup_dir/logs" .
        log "已恢复 logs 目录"
    fi
    
    log "数据恢复完成"
}

# 显示帮助信息
show_help() {
    echo "房价数据可视化系统 Docker 管理脚本"
    echo ""
    echo "用法: $0 <命令> [参数]"
    echo ""
    echo "服务管理命令:"
    echo "  start-web        - 启动Web服务"
    echo "  stop-web         - 停止Web服务"
    echo "  restart-web      - 重启Web服务"
    echo "  start-all        - 启动所有服务"
    echo "  stop-all         - 停止所有服务"
    echo "  restart-all      - 重启所有服务"
    echo "  status           - 查看服务状态"
    echo ""
    echo "数据操作命令:"
    echo "  collect          - 执行数据采集"
    echo "  process          - 执行数据处理"
    echo "  batch            - 执行批量处理"
    echo "  update           - 执行完整数据更新流程"
    echo ""
    echo "维护命令:"
    echo "  build            - 构建Docker镜像"
    echo "  logs [service]   - 查看服务日志 (默认: house-price-web)"
    echo "  exec [service]   - 进入容器 (默认: house-price-web)"
    echo "  cleanup          - 清理Docker资源"
    echo "  backup           - 备份数据"
    echo "  restore <dir>    - 恢复数据"
    echo ""
    echo "示例:"
    echo "  $0 start-web     # 启动Web服务"
    echo "  $0 update        # 更新所有数据"
    echo "  $0 logs          # 查看Web服务日志"
    echo "  $0 backup        # 备份数据"
    echo ""
}

# 主函数
main() {
    # 检查Docker环境
    check_docker
    check_project
    
    case "${1:-}" in
        start-web)
            start_web
            ;;
        stop-web)
            stop_web
            ;;
        restart-web)
            restart_web
            ;;
        start-all)
            start_all
            ;;
        stop-all)
            stop_all
            ;;
        restart-all)
            restart_all
            ;;
        status)
            status
            ;;
        collect)
            collect_data
            ;;
        process)
            process_data
            ;;
        batch)
            batch_process
            ;;
        update)
            update_data
            ;;
        build)
            build_images
            ;;
        logs)
            logs "$2"
            ;;
        exec)
            exec_container "$2"
            ;;
        cleanup)
            cleanup
            ;;
        backup)
            backup_data
            ;;
        restore)
            restore_data "$2"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "未知命令: ${1:-}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
