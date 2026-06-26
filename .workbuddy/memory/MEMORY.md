# HousePrice 房价数据可视化系统 - 项目记忆

## 项目概述
房价数据可视化系统，从国家统计局获取70个大中城市的房价数据，提供交互式图表展示和数据分析功能。

## 部署方式
### 本地部署（推荐）
```bash
cd /Users/wangwenye/Github/HousePrice
python3 web_server.py --host 0.0.0.0 --port 8000
```

### Docker部署（需要Docker环境）
```bash
./docker-start.sh
```

## 数据更新
### 自动更新（推荐）
```bash
cd /Users/wangwenye/Github/HousePrice
/opt/anaconda3/bin/python3 update_house_price_urls.py --auto-collect
```

### 手动更新
1. 更新URL列表：`python3 update_house_price_urls.py`
2. 采集数据：`python3 data_collector.py`
3. 处理数据：`python3 city_price_processor.py`

## 项目结构
- `web_server.py` - Web可视化服务器（端口8000）
- `update_house_price_urls.py` - 数据更新脚本（含自动采集）
- `data_collector.py` - 数据采集模块
- `city_price_processor.py` - 城市房价处理脚本
- `batch_process_all_cities.py` - 批量处理脚本
- `web/` - Web界面文件（HTML/CSS/JS）
- `results/` - 处理后的JSON数据文件
- `collected_data/` - 原始XML数据文件

## 依赖环境
- Python 3.12+ (系统Python: /opt/anaconda3/bin/python3)
- 依赖包：requests, beautifulsoup4, pandas, openpyxl, lxml, flask, flask-cors

## 访问地址
- 本地：http://localhost:8000
- 局域网：http://<IP地址>:8000

## 注意事项
1. 数据更新需要网络连接（访问国家统计局网站）
2. 数据更新可能需要几分钟时间
3. 部分城市可能缺少分类指数数据（显示为"无数据"）
4. 使用系统Python而非WorkBuddy Python环境（避免依赖缺失）

## 历史记录
- 2026-06-10: 成功部署并更新2026年4月房价数据
- 2026-04-24: 项目初始部署