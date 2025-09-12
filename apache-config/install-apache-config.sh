#!/bin/bash
# Apache配置安装脚本 - 房价数据可视化系统

set -e

# 配置变量
PROJECT_DIR="/Users/wangwenye/Github/HousePrice"
APACHE_SITES_DIR="/etc/apache2/sites-available"
APACHE_SITES_ENABLED="/etc/apache2/sites-enabled"
SYSTEMD_DIR="/etc/systemd/system"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查是否以root身份运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "请以root身份运行此脚本"
        exit 1
    fi
}

# 检查Apache是否安装
check_apache() {
    if ! command -v apache2 &> /dev/null; then
        error "Apache2未安装，请先安装Apache2"
        info "Ubuntu/Debian: sudo apt-get install apache2"
        info "CentOS/RHEL: sudo yum install httpd"
        exit 1
    fi
    
    log "Apache2已安装"
}

# 启用必要的Apache模块
enable_apache_modules() {
    log "启用必要的Apache模块..."
    
    local modules=(
        "rewrite"
        "proxy"
        "proxy_http"
        "headers"
        "expires"
        "deflate"
        "ssl"
    )
    
    for module in "${modules[@]}"; do
        if a2enmod "$module" >/dev/null 2>&1; then
            log "模块 $module 已启用"
        else
            warn "模块 $module 启用失败或已启用"
        fi
    done
}

# 安装反向代理配置
install_proxy_config() {
    log "安装Apache反向代理配置..."
    
    local config_file="house-price-proxy.conf"
    local source_file="$PROJECT_DIR/apache-config/$config_file"
    local target_file="$APACHE_SITES_DIR/$config_file"
    
    if [ ! -f "$source_file" ]; then
        error "配置文件不存在: $source_file"
        return 1
    fi
    
    # 复制配置文件
    cp "$source_file" "$target_file"
    log "配置文件已复制到: $target_file"
    
    # 提示用户修改配置
    warn "请编辑 $target_file 并修改以下内容:"
    echo "  - ServerName your-domain.com (修改为您的域名)"
    echo "  - SSL证书路径 (如果使用HTTPS)"
    echo "  - 项目路径 (如果不是默认路径)"
    
    # 启用站点
    if a2ensite "$config_file" >/dev/null 2>&1; then
        log "站点 $config_file 已启用"
    else
        error "站点启用失败"
        return 1
    fi
    
    return 0
}

# 安装HTTP-only反向代理配置
install_http_only_config() {
    log "安装Apache HTTP-only反向代理配置..."
    
    local config_file="house-price-http-only.conf"
    local source_file="$PROJECT_DIR/apache-config/$config_file"
    local target_file="$APACHE_SITES_DIR/$config_file"
    
    if [ ! -f "$source_file" ]; then
        error "配置文件不存在: $source_file"
        return 1
    fi
    
    # 复制配置文件
    cp "$source_file" "$target_file"
    log "HTTP-only配置文件已复制到: $target_file"
    
    # 提示用户修改配置
    warn "请编辑 $target_file 并修改以下内容:"
    echo "  - ServerName wenye.wang (已设置为您的域名)"
    echo "  - 项目路径 (如果不是默认路径)"
    
    # 启用站点
    if a2ensite "$config_file" >/dev/null 2>&1; then
        log "站点 $config_file 已启用"
    else
        error "站点启用失败"
        return 1
    fi
    
    return 0
}

# 安装WSGI配置
install_wsgi_config() {
    log "安装Apache WSGI配置..."
    
    # 检查mod_wsgi
    if ! apache2ctl -M | grep -q wsgi; then
        warn "mod_wsgi未安装，正在安装..."
        if command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y libapache2-mod-wsgi-py3
        elif command -v yum &> /dev/null; then
            yum install -y python3-mod_wsgi
        else
            error "无法自动安装mod_wsgi，请手动安装"
            return 1
        fi
        
        a2enmod wsgi
        log "mod_wsgi已安装并启用"
    fi
    
    local config_file="house-price-vhost.conf"
    local source_file="$PROJECT_DIR/apache-config/$config_file"
    local target_file="$APACHE_SITES_DIR/$config_file"
    
    if [ ! -f "$source_file" ]; then
        error "配置文件不存在: $source_file"
        return 1
    fi
    
    # 复制配置文件
    cp "$source_file" "$target_file"
    log "WSGI配置文件已复制到: $target_file"
    
    # 提示用户修改配置
    warn "请编辑 $target_file 并修改以下内容:"
    echo "  - ServerName your-domain.com (修改为您的域名)"
    echo "  - SSL证书路径 (如果使用HTTPS)"
    echo "  - Python环境路径"
    echo "  - 项目路径"
    
    return 0
}

# 安装systemd服务
install_systemd_service() {
    log "安装systemd服务..."
    
    local service_file="house-price.service"
    local source_file="$PROJECT_DIR/apache-config/$service_file"
    local target_file="$SYSTEMD_DIR/$service_file"
    
    if [ ! -f "$source_file" ]; then
        error "服务文件不存在: $source_file"
        return 1
    fi
    
    # 复制服务文件
    cp "$source_file" "$target_file"
    log "服务文件已复制到: $target_file"
    
    # 重载systemd
    systemctl daemon-reload
    log "systemd配置已重载"
    
    # 启用服务
    systemctl enable house-price.service
    log "house-price服务已设置为开机自启"
    
    warn "请编辑 $target_file 并修改以下内容:"
    echo "  - User和Group (根据您的系统设置)"
    echo "  - 项目路径"
    echo "  - Python环境路径"
    
    return 0
}

# 设置文件权限
setup_permissions() {
    log "设置文件权限..."
    
    # 创建www-data用户（如果不存在）
    if ! id "www-data" &>/dev/null; then
        warn "www-data用户不存在，请根据您的系统创建适当的用户"
    fi
    
    # 设置项目目录权限
    chown -R www-data:www-data "$PROJECT_DIR/results" 2>/dev/null || warn "无法设置results目录权限"
    chmod -R 755 "$PROJECT_DIR/web" 2>/dev/null || warn "无法设置web目录权限"
    chmod +x "$PROJECT_DIR/apache-config/house-price.wsgi" 2>/dev/null || warn "无法设置WSGI文件权限"
    
    log "权限设置完成"
}

# 测试Apache配置
test_apache_config() {
    log "测试Apache配置..."
    
    if apache2ctl configtest >/dev/null 2>&1; then
        log "Apache配置测试通过"
        return 0
    else
        error "Apache配置测试失败"
        apache2ctl configtest
        return 1
    fi
}

# 主菜单
show_menu() {
    echo ""
    echo "========================================"
    echo "  房价数据可视化系统 - Apache配置安装"
    echo "========================================"
    echo ""
    echo "1. 安装反向代理配置 (包含HTTPS)"
    echo "2. 安装HTTP-only反向代理配置 (推荐)"
    echo "3. 安装WSGI配置"
    echo "4. 安装systemd服务"
    echo "5. 完整安装 (HTTP-only + systemd)"
    echo "6. 测试Apache配置"
    echo "7. 重启Apache服务"
    echo "0. 退出"
    echo ""
}

# 主函数
main() {
    check_root
    check_apache
    enable_apache_modules
    
    if [ $# -eq 0 ]; then
        # 交互模式
        while true; do
            show_menu
            read -p "请选择操作 [0-7]: " choice
            
            case $choice in
                1)
                    install_proxy_config
                    setup_permissions
                    test_apache_config
                    ;;
                2)
                    install_http_only_config
                    setup_permissions
                    test_apache_config
                    ;;
                3)
                    install_wsgi_config
                    setup_permissions
                    test_apache_config
                    ;;
                4)
                    install_systemd_service
                    ;;
                5)
                    install_http_only_config
                    install_systemd_service
                    setup_permissions
                    test_apache_config
                    ;;
                6)
                    test_apache_config
                    ;;
                7)
                    log "重启Apache服务..."
                    systemctl restart apache2
                    log "Apache服务已重启"
                    ;;
                0)
                    log "退出安装程序"
                    exit 0
                    ;;
                *)
                    error "无效选择，请重新输入"
                    ;;
            esac
            
            echo ""
            read -p "按回车键继续..."
        done
    else
        # 命令行模式
        case "$1" in
            proxy)
                install_proxy_config
                setup_permissions
                test_apache_config
                ;;
            http-only)
                install_http_only_config
                setup_permissions
                test_apache_config
                ;;
            wsgi)
                install_wsgi_config
                setup_permissions
                test_apache_config
                ;;
            service)
                install_systemd_service
                ;;
            full)
                install_http_only_config
                install_systemd_service
                setup_permissions
                test_apache_config
                ;;
            test)
                test_apache_config
                ;;
            *)
                echo "用法: $0 [proxy|http-only|wsgi|service|full|test]"
                echo ""
                echo "选项说明:"
                echo "  proxy     - 安装反向代理配置 (包含HTTPS)"
                echo "  http-only - 安装HTTP-only反向代理配置 (推荐)"
                echo "  wsgi      - 安装WSGI配置"
                echo "  service   - 安装systemd服务"
                echo "  full      - 完整安装 (HTTP-only + systemd)"
                echo "  test      - 测试Apache配置"
                exit 1
                ;;
        esac
    fi
}

main "$@"
