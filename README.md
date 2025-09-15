# 房价数据可视化系统

一个基于Docker的房价数据可视化系统，从国家统计局获取70个大中城市的房价数据，提供交互式图表展示和数据分析功能。

## ✨ 功能特性

- 🏠 **房价数据采集**：自动从国家统计局获取最新房价数据
- 📊 **数据可视化**：交互式图表展示房价指数变化趋势
- 🏙️ **多城市支持**：支持70个大中城市的房价数据
- 📈 **多维度分析**：新建商品住宅、二手住宅、分类指数等
- 🔄 **自动更新**：支持定时数据更新和批量处理
- 🐳 **Docker部署**：容器化部署，简单易用

## 🚀 快速开始

### 环境要求
- Docker 20.10+
- Docker Compose 2.0+

### 一键启动
```bash
# 克隆项目
git clone <repository-url>
cd HousePrice

# 一键启动
./docker-start.sh

# 访问应用
# http://localhost:8000
```

## 📋 详细使用

### 服务管理
```bash
./docker-manage.sh start-web      # 启动Web服务
./docker-manage.sh stop-all       # 停止所有服务
./docker-manage.sh status         # 查看服务状态
./docker-manage.sh logs           # 查看日志
```

### 数据操作
```bash
./docker-manage.sh update         # 完整数据更新流程
./docker-manage.sh collect        # 执行数据采集
./docker-manage.sh process        # 执行数据处理
./docker-manage.sh backup         # 备份数据
```

### 维护操作
```bash
./docker-manage.sh build          # 重新构建镜像
./docker-manage.sh cleanup        # 清理Docker资源
./docker-manage.sh exec           # 进入容器调试
```

## 📁 项目结构

```
HousePrice/
├── README.md                     # 项目说明文档
├── Dockerfile                    # Docker镜像构建文件
├── docker-compose.yml            # Docker Compose配置
├── docker-manage.sh              # Docker管理脚本
├── docker-start.sh               # Docker快速启动脚本
├── test-docker.sh                # Docker配置测试脚本
├── web_server.py                 # Web可视化服务器
├── web/                          # Web界面文件
│   ├── index.html               # 主页面
│   ├── style.css                # 样式文件
│   └── app.js                   # 前端逻辑
├── data_collector.py             # 数据采集模块
├── city_price_processor.py       # 城市房价处理脚本
├── batch_process_all_cities.py   # 批量处理脚本
├── update_house_price_urls.py    # URL自动更新脚本
├── results/                      # 处理后的JSON数据
├── collected_data/               # 原始XML数据
└── requirements.txt              # Python依赖
```

## 🎯 核心功能

### 数据采集
- 自动从国家统计局网站采集房价数据
- 支持XML格式数据存储
- 智能数据解析和清理
- 自动去重和合并

### 数据处理
- XML数据转换为JSON格式
- 支持四种房价指数类型：
  - 新建商品住宅销售价格指数
  - 二手住宅销售价格指数
  - 新建商品住宅销售价格分类指数
  - 二手住宅销售价格分类指数
- 环比同比交叉验证矫正算法

### Web可视化
- 响应式设计，支持桌面和移动设备
- 交互式图表展示价格变化趋势
- 多城市对比功能
- 实时数据更新

## 🏗️ Docker架构

### 服务组件
- **house-price-web**: Web可视化服务（端口8000）
- **house-price-collector**: 数据采集服务
- **house-price-processor**: 数据处理服务
- **house-price-batch**: 批量处理服务

### 数据持久化
- `collected_data/`: 原始XML数据
- `results/`: 处理后的JSON数据
- `logs/`: 应用日志

## 🔧 技术栈

- **后端**: Python 3.11, Flask
- **前端**: HTML5, CSS3, JavaScript, Chart.js
- **部署**: Docker, Docker Compose
- **数据**: XML, JSON, pandas
- **可视化**: Chart.js图表库

## 📊 数据说明

### 数据来源
数据来自国家统计局，包含四个主要表格：
1. 70个大中城市新建商品住宅销售价格指数
2. 70个大中城市二手住宅销售价格指数
3. 70个大中城市新建商品住宅销售价格分类指数
4. 70个大中城市二手住宅销售价格分类指数

### 数据特点
- **时间范围**: 2020年11月至最新数据
- **城市覆盖**: 70个大中城市
- **更新频率**: 每月更新
- **数据精度**: 环比同比交叉验证矫正

## 🛠️ 开发说明

### 本地开发
```bash
# 安装依赖
pip install -r requirements.txt

# 启动Web服务
python web_server.py

# 数据采集
python data_collector.py

# 数据处理
python city_price_processor.py
```

### Docker开发
```bash
# 构建镜像
docker compose build

# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f
```

## 🔍 故障排除

### 常见问题

**1. Docker服务启动失败**
```bash
# 检查Docker状态
docker ps -a

# 查看详细日志
./docker-manage.sh logs

# 重新构建镜像
./docker-manage.sh build
```

**2. 数据更新失败**
```bash
# 检查网络连接
docker run --rm curlimages/curl curl -I https://www.stats.gov.cn

# 手动执行数据采集
./docker-manage.sh collect
```

**3. 端口被占用**
```bash
# 检查端口占用
lsof -i :8000

# 停止占用端口的进程
./docker-manage.sh stop-all
```

### 调试命令
```bash
# 进入容器调试
./docker-manage.sh exec house-price-web

# 查看服务状态
./docker-manage.sh status

# 测试Docker配置
./test-docker.sh
```

## 📈 性能优化

### Docker优化
- 使用Python 3.11-slim轻量级镜像
- 多阶段构建减少镜像大小
- 健康检查机制
- 资源限制配置

### 应用优化
- 静态文件缓存
- JSON数据压缩
- 数据库查询优化
- 图表渲染优化

## 🔒 安全特性

- 非root用户运行
- 容器隔离
- 数据持久化保护
- 健康检查监控

## 📝 更新日志

### v2.0.0 (2025-09-15)
- ✅ 完成Docker容器化部署
- ✅ 简化项目结构，移除Apache配置
- ✅ 优化文档结构，整合为单一README
- ✅ 完善Docker管理脚本
- ✅ 添加健康检查和监控

### v1.0.0 (2025-09-12)
- ✅ 基础房价数据采集功能
- ✅ Web可视化界面
- ✅ 数据处理和矫正算法
- ✅ 批量处理功能

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送邮件
- 项目讨论区

---

**🎉 感谢使用房价数据可视化系统！**