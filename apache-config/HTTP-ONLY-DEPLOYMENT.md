# Apache HTTP-only 部署指南

## 概述

本指南专门针对只使用HTTP（不使用HTTPS）的部署场景。如果您不需要SSL证书，可以使用这个简化的配置。

## 快速部署

### 方式1：使用自动安装脚本（推荐）

```bash
# 以root身份运行安装脚本
sudo ./apache-config/install-apache-config.sh

# 选择选项 2: 安装HTTP-only反向代理配置 (推荐)
# 或选择选项 5: 完整安装 (HTTP-only + systemd)

# 或者直接使用命令行
sudo ./apache-config/install-apache-config.sh http-only
```

### 方式2：手动安装

```bash
# 1. 复制HTTP-only配置文件
sudo cp apache-config/house-price-http-only.conf /etc/apache2/sites-available/

# 2. 启用必要的Apache模块（不需要SSL模块）
sudo a2enmod proxy proxy_http headers expires deflate rewrite

# 3. 启用站点
sudo a2ensite house-price-http-only.conf

# 4. 测试配置
sudo apache2ctl configtest

# 5. 重启Apache
sudo systemctl restart apache2
```

## 配置文件说明

### house-price-http-only.conf 特点

- ✅ **仅HTTP**：不包含任何SSL/HTTPS配置
- ✅ **域名已设置**：ServerName 已设置为 `wenye.wang`
- ✅ **路径已配置**：项目路径已设置为您的实际路径
- ✅ **性能优化**：静态文件缓存、GZIP压缩
- ✅ **安全头**：基本的安全HTTP头设置

### 配置内容

```apache
<VirtualHost *:80>
    ServerName wenye.wang
    DocumentRoot /Users/wangwenye/Github/HousePrice/web
    
    # 静态文件直接由Apache提供
    <Directory "/Users/wangwenye/Github/HousePrice/web">
        # 缓存和权限配置
    </Directory>
    
    # API请求代理到Python后端
    ProxyPass /api/ http://127.0.0.1:8000/api/
    ProxyPassReverse /api/ http://127.0.0.1:8000/api/
    
    # 日志、安全头、压缩配置
</VirtualHost>
```

## 启动Python后端服务

### 方式1：使用systemd服务（推荐）

```bash
# 安装systemd服务
sudo ./apache-config/install-apache-config.sh service

# 启动服务
sudo systemctl start house-price.service

# 设置开机自启
sudo systemctl enable house-price.service

# 查看状态
sudo systemctl status house-price.service
```

### 方式2：使用启动脚本

```bash
# 启动服务
sudo ./apache-config/start-house-price.sh start

# 查看状态
./apache-config/start-house-price.sh status

# 查看日志
./apache-config/start-house-price.sh logs
```

### 方式3：手动启动

```bash
# 进入项目目录
cd /Users/wangwenye/Github/HousePrice

# 启动Python服务
python3 web_server.py --host 127.0.0.1 --port 8000
```

## 验证部署

### 1. 检查Apache配置

```bash
sudo apache2ctl configtest
```

应该显示：`Syntax OK`

### 2. 检查服务状态

```bash
# 检查Apache状态
sudo systemctl status apache2

# 检查Python服务状态（如果使用systemd）
sudo systemctl status house-price.service
```

### 3. 测试网站访问

```bash
# 测试主页
curl http://wenye.wang/

# 测试API接口
curl http://wenye.wang/api/cities

# 测试数据接口
curl http://wenye.wang/api/data/new_house_basic_index.json
```

### 4. 浏览器访问

在浏览器中打开：`http://wenye.wang`

## 故障排除

### 常见问题

**1. Apache配置错误**
```bash
# 检查配置语法
sudo apache2ctl configtest

# 查看错误日志
sudo tail -f /var/log/apache2/error.log
```

**2. Python服务无法启动**
```bash
# 检查端口是否被占用
sudo lsof -i :8000

# 查看systemd日志
sudo journalctl -u house-price.service -f

# 手动启动测试
python3 web_server.py --host 127.0.0.1 --port 8000
```

**3. 权限问题**
```bash
# 设置正确的文件权限
sudo chown -R www-data:www-data /Users/wangwenye/Github/HousePrice/results
sudo chmod -R 755 /Users/wangwenye/Github/HousePrice/web
```

**4. 域名解析问题**
```bash
# 检查域名解析
nslookup wenye.wang

# 如果使用本地测试，可以修改hosts文件
echo "127.0.0.1 wenye.wang" | sudo tee -a /etc/hosts
```

### 日志查看

```bash
# Apache访问日志
sudo tail -f /var/log/apache2/house-price-access.log

# Apache错误日志
sudo tail -f /var/log/apache2/house-price-error.log

# Python服务日志（systemd）
sudo journalctl -u house-price.service -f

# Python服务日志（手动启动）
tail -f /var/log/house-price.log
```

## 性能优化

### 1. 启用更多缓存模块

```bash
sudo a2enmod cache cache_disk
```

### 2. 调整Apache配置

在虚拟主机配置中添加：

```apache
# 启用缓存
<Location />
    CacheEnable disk
    CacheRoot /var/cache/apache2/mod_cache_disk
</Location>
```

### 3. 监控性能

```bash
# 启用状态模块
sudo a2enmod status

# 访问状态页面
# http://wenye.wang/server-status
```

## 维护命令

```bash
# 重启Apache
sudo systemctl restart apache2

# 重启Python服务
sudo systemctl restart house-price.service

# 重新加载Apache配置
sudo systemctl reload apache2

# 查看所有启用的站点
sudo a2ensite --list

# 禁用站点
sudo a2dissite house-price-http-only.conf
```

## 总结

使用HTTP-only配置的优势：

- ✅ **简单部署**：无需SSL证书配置
- ✅ **快速启动**：减少配置复杂度
- ✅ **适合内网**：内网环境下的理想选择
- ✅ **开发测试**：开发和测试环境的完美选择
- ✅ **性能良好**：静态文件直接由Apache提供

现在您可以通过 `http://wenye.wang` 访问您的房价数据可视化系统了！
