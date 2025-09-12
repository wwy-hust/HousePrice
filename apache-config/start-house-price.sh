#!/bin/bash
# 房价数据可视化系统启动脚本

set -e

# 配置变量
PROJECT_DIR="/Users/wangwenye/Github/HousePrice"
PYTHON_BIN="python3"
SERVER_HOST="127.0.0.1"
SERVER_PORT="8000"
PID_FILE="/var/run/house-price.pid"
LOG_FILE="/var/log/house-price.log"
USER="www-data"  # 根据系统调整

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# 检查是否以root身份运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "请以root身份运行此脚本"
        exit 1
    fi
}

# 检查项目目录
check_project() {
    if [ ! -d "$PROJECT_DIR" ]; then
        error "项目目录不存在: $PROJECT_DIR"
        exit 1
    fi
    
    if [ ! -f "$PROJECT_DIR/web_server.py" ]; then
        error "web_server.py不存在"
        exit 1
    fi
    
    if [ ! -d "$PROJECT_DIR/web" ]; then
        error "web目录不存在"
        exit 1
    fi
    
    if [ ! -d "$PROJECT_DIR/results" ]; then
        error "results目录不存在"
        exit 1
    fi
}

# 检查Python依赖
check_dependencies() {
    log "检查Python依赖..."
    
    if ! command -v $PYTHON_BIN &> /dev/null; then
        error "Python3未安装"
        exit 1
    fi
    
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        log "安装Python依赖..."
        cd "$PROJECT_DIR"
        $PYTHON_BIN -m pip install -r requirements.txt
    fi
}

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$SERVER_PORT -sTCP:LISTEN -t >/dev/null ; then
        warn "端口 $SERVER_PORT 已被占用"
        if [ -f "$PID_FILE" ]; then
            local old_pid=$(cat "$PID_FILE")
            if kill -0 "$old_pid" 2>/dev/null; then
                log "停止旧的进程 (PID: $old_pid)"
                kill "$old_pid"
                sleep 2
            fi
        fi
        
        # 强制杀死占用端口的进程
        local pid=$(lsof -ti:$SERVER_PORT)
        if [ ! -z "$pid" ]; then
            log "强制停止占用端口的进程: $pid"
            kill -9 $pid
        fi
    fi
}

# 启动服务
start_service() {
    log "启动房价数据可视化服务..."
    
    cd "$PROJECT_DIR"
    
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    chown $USER:$USER "$LOG_FILE"
    
    # 启动服务
    sudo -u $USER $PYTHON_BIN web_server.py \
        --host $SERVER_HOST \
        --port $SERVER_PORT \
        > "$LOG_FILE" 2>&1 &
    
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # 等待服务启动
    sleep 3
    
    if kill -0 "$pid" 2>/dev/null; then
        log "服务启动成功 (PID: $pid)"
        log "服务地址: http://$SERVER_HOST:$SERVER_PORT"
        log "日志文件: $LOG_FILE"
        return 0
    else
        error "服务启动失败"
        if [ -f "$LOG_FILE" ]; then
            error "错误日志:"
            tail -n 20 "$LOG_FILE"
        fi
        return 1
    fi
}

# 停止服务
stop_service() {
    log "停止房价数据可视化服务..."
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            sleep 2
            
            if kill -0 "$pid" 2>/dev/null; then
                warn "进程未响应，强制停止"
                kill -9 "$pid"
            fi
            
            log "服务已停止"
        else
            warn "进程不存在或已停止"
        fi
        rm -f "$PID_FILE"
    else
        warn "PID文件不存在"
    fi
    
    # 清理端口
    local pid=$(lsof -ti:$SERVER_PORT 2>/dev/null)
    if [ ! -z "$pid" ]; then
        log "清理端口占用进程: $pid"
        kill -9 $pid
    fi
}

# 检查服务状态
status_service() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "服务正在运行 (PID: $pid)"
            log "服务地址: http://$SERVER_HOST:$SERVER_PORT"
            return 0
        else
            warn "PID文件存在但进程不存在"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        warn "服务未运行"
        return 1
    fi
}

# 重启服务
restart_service() {
    log "重启房价数据可视化服务..."
    stop_service
    sleep 2
    start_service
}

# 查看日志
view_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        error "日志文件不存在: $LOG_FILE"
        exit 1
    fi
}

# 主函数
main() {
    case "${1:-}" in
        start)
            check_root
            check_project
            check_dependencies
            check_port
            start_service
            ;;
        stop)
            check_root
            stop_service
            ;;
        restart)
            check_root
            restart_service
            ;;
        status)
            status_service
            ;;
        logs)
            view_logs
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status|logs}"
            echo ""
            echo "命令说明:"
            echo "  start   - 启动服务"
            echo "  stop    - 停止服务"
            echo "  restart - 重启服务"
            echo "  status  - 检查服务状态"
            echo "  logs    - 查看实时日志"
            exit 1
            ;;
    esac
}

main "$@"
