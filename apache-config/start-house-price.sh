#!/bin/bash
# 房价数据可视化系统启动脚本

set -e

# 配置变量
PROJECT_DIR="/Users/wangwenye/Github/HousePrice"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_BIN="python3"  # 默认Python，会被venv中的Python覆盖
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

# 检查并设置venv环境
setup_venv() {
    log "检查Python虚拟环境..."
    
    if [ -d "$VENV_DIR" ]; then
        log "发现虚拟环境: $VENV_DIR"
        
        # 检查venv中的Python是否存在
        local venv_python="$VENV_DIR/bin/python"
        if [ -f "$venv_python" ]; then
            # 设置venv目录的权限，确保www-data用户可以访问
            log "设置虚拟环境权限..."
            chmod -R 755 "$VENV_DIR"
            chown -R $USER:$USER "$VENV_DIR" 2>/dev/null || warn "无法设置venv目录所有者"
            
            # 确保Python可执行文件有执行权限
            chmod +x "$venv_python" 2>/dev/null || warn "无法设置Python执行权限"
            
            PYTHON_BIN="$venv_python"
            log "使用虚拟环境中的Python: $PYTHON_BIN"
            
            # 检查Python版本
            local python_version=$($PYTHON_BIN --version 2>&1)
            log "Python版本: $python_version"
            
            return 0
        else
            warn "虚拟环境目录存在但Python可执行文件不存在"
            warn "将使用系统默认Python"
        fi
    else
        warn "虚拟环境目录不存在: $VENV_DIR"
        warn "将使用系统默认Python"
        
        # 提示用户创建虚拟环境
        info "建议创建虚拟环境:"
        info "  cd $PROJECT_DIR"
        info "  python3 -m venv venv"
        info "  source venv/bin/activate"
        info "  pip install -r requirements.txt"
    fi
    
    # 使用系统默认Python
    if ! command -v $PYTHON_BIN &> /dev/null; then
        error "Python3未安装"
        exit 1
    fi
    
    local python_version=$($PYTHON_BIN --version 2>&1)
    log "使用系统Python: $python_version"
}

# 检查Python依赖
check_dependencies() {
    log "检查Python依赖..."
    
    if ! command -v $PYTHON_BIN &> /dev/null; then
        error "Python未安装或路径不正确: $PYTHON_BIN"
        exit 1
    fi
    
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        log "安装Python依赖..."
        cd "$PROJECT_DIR"
        
        # 如果在venv环境中，直接使用pip
        if [[ "$PYTHON_BIN" == *"$VENV_DIR"* ]]; then
            log "在虚拟环境中安装依赖..."
            $PYTHON_BIN -m pip install -r requirements.txt
        else
            log "在系统环境中安装依赖..."
            $PYTHON_BIN -m pip install --user -r requirements.txt
        fi
    else
        warn "requirements.txt文件不存在，跳过依赖安装"
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

# 修复venv权限
fix_venv_permissions() {
    log "修复虚拟环境权限..."
    
    if [ ! -d "$VENV_DIR" ]; then
        error "虚拟环境目录不存在: $VENV_DIR"
        exit 1
    fi
    
    # 设置venv目录权限
    log "设置虚拟环境权限..."
    chmod -R 755 "$VENV_DIR"
    chown -R $USER:$USER "$VENV_DIR" 2>/dev/null || warn "无法设置venv目录所有者"
    
    # 确保Python可执行文件有执行权限
    local venv_python="$VENV_DIR/bin/python"
    if [ -f "$venv_python" ]; then
        chmod +x "$venv_python" 2>/dev/null || warn "无法设置Python执行权限"
        log "Python权限修复完成: $venv_python"
    else
        error "Python可执行文件不存在: $venv_python"
        exit 1
    fi
    
    # 修复其他可执行文件权限
    find "$VENV_DIR/bin" -type f -name "*" -exec chmod +x {} \; 2>/dev/null || warn "无法设置bin目录文件权限"
    
    log "虚拟环境权限修复完成"
}

# 创建虚拟环境
create_venv() {
    log "创建Python虚拟环境..."
    
    if [ -d "$VENV_DIR" ]; then
        warn "虚拟环境已存在: $VENV_DIR"
        read -p "是否重新创建? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log "删除现有虚拟环境..."
            rm -rf "$VENV_DIR"
        else
            log "使用现有虚拟环境"
            return 0
        fi
    fi
    
    cd "$PROJECT_DIR"
    
    # 检查系统Python
    if ! command -v python3 &> /dev/null; then
        error "系统Python3未安装，无法创建虚拟环境"
        exit 1
    fi
    
    # 创建虚拟环境
    log "创建虚拟环境: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    
    if [ $? -eq 0 ]; then
        log "虚拟环境创建成功"
        
        # 设置虚拟环境权限
        log "设置虚拟环境权限..."
        chmod -R 755 "$VENV_DIR"
        chown -R $USER:$USER "$VENV_DIR" 2>/dev/null || warn "无法设置venv目录所有者"
        
        # 确保Python可执行文件有执行权限
        chmod +x "$VENV_DIR/bin/python" 2>/dev/null || warn "无法设置Python执行权限"
        
        # 激活虚拟环境并安装依赖
        log "激活虚拟环境并安装依赖..."
        source "$VENV_DIR/bin/activate"
        
        if [ -f "$PROJECT_DIR/requirements.txt" ]; then
            log "安装Python依赖..."
            pip install -r requirements.txt
        fi
        
        log "虚拟环境设置完成"
        log "Python路径: $VENV_DIR/bin/python"
    else
        error "虚拟环境创建失败"
        exit 1
    fi
}

# 主函数
main() {
    case "${1:-}" in
        start)
            check_root
            check_project
            setup_venv
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
        create-venv)
            check_root
            check_project
            create_venv
            ;;
        fix-permissions)
            check_root
            check_project
            fix_venv_permissions
            ;;
        *)
            echo "用法: $0 {start|stop|restart|status|logs|create-venv|fix-permissions}"
            echo ""
            echo "命令说明:"
            echo "  start          - 启动服务"
            echo "  stop           - 停止服务"
            echo "  restart        - 重启服务"
            echo "  status         - 检查服务状态"
            echo "  logs           - 查看实时日志"
            echo "  create-venv    - 创建Python虚拟环境"
            echo "  fix-permissions - 修复venv权限问题"
            echo ""
            echo "注意:"
            echo "  - 脚本会自动检测并使用项目目录下的venv虚拟环境"
            echo "  - 如果venv不存在，将使用系统默认Python"
            echo "  - 建议先运行 'create-venv' 创建虚拟环境"
            echo "  - 如果遇到权限问题，运行 'fix-permissions' 修复"
            exit 1
            ;;
    esac
}

main "$@"
