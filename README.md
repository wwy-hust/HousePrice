# 房价信息展示网站

这是一个展示70个大中城市房价信息的网站项目。

## 功能特性

- 从国家统计局获取房价数据
- 展示70个大中城市的新建商品住宅和二手住宅销售价格指数
- 提供数据分析和可视化功能

## 数据来源

数据来自国家统计局，包含四个表格：
1. 70个大中城市新建商品住宅销售价格指数
2. 70个大中城市二手住宅销售价格指数  
3. 70个大中城市新建商品住宅销售价格分类指数
4. 70个大中城市二手住宅销售价格分类指数

## 项目结构

```
HousePrice/
├── README.md                 # 项目说明文档
├── requirements.txt          # Python依赖包
├── app.py                   # Flask Web应用主文件
├── data_collector.py        # 数据采集模块
├── data_manager.py          # 数据管理模块
├── HousePriceURL.xlsx       # 数据源URL列表
├── collected_data/          # 采集的数据存储目录
├── templates/               # HTML模板
└── static/                  # 静态资源文件
```

## 安装和运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行数据采集：
```bash
python data_collector.py
```

3. 启动Web应用：
```bash
python app.py
```

## URL数据采集接口

### 基本使用

1. **使用数据采集器类**：
```python
from data_collector import HousePriceDataCollector

collector = HousePriceDataCollector()
success = collector.collect_single_url_data(
    url="https://www.stats.gov.cn/sj/zxfb/202508/t20250815_1960781.html",
    description="2025年7月份房价数据",
    date="2025-08-15"
)
```

2. **使用命令行接口**：
```bash
python url_collector_api.py "https://www.stats.gov.cn/sj/zxfb/202508/t20250815_1960781.html" -d "2025年7月份房价数据" -t "2025-08-15"
```

3. **批量采集**：
```python
# 从CSV文件加载URL列表并批量采集
collector = HousePriceDataCollector()
url_df = collector.load_url_list()
for index, row in url_df.iterrows():
    collector.collect_single_url_data(row['标题链接'], row['标题'], row['时间'])
```

### 数据格式

采集的数据以XML格式存储，包含以下结构：
- 根元素：`house_price_data`
- 属性：`source_url`, `description`, `date`, `collected_at`
- 子元素：多个`table`元素，每个表格包含列名和数据行

### 验证数据

使用验证脚本检查XML数据结构：
```bash
python test_xml_structure.py
```

## 项目文件说明

### 核心文件
- `data_collector.py` - 主要的数据采集器类
- `url_collector_api.py` - 命令行接口，用于单个URL数据采集
- `test_xml_structure.py` - XML数据结构验证工具
- `example_usage.py` - 使用示例和演示代码

### 数据文件
- `HousePriceURL.csv` - 包含58个统计局URL的CSV文件
- `collected_data/` - 存储采集的XML数据文件

### 运行示例
```bash
# 运行使用示例
python example_usage.py

# 验证XML数据结构
python test_xml_structure.py

# 采集单个URL
python url_collector_api.py "URL" -d "描述" -t "日期"
```

## 开发进度

- [x] 项目基础结构
- [x] URL数据采集接口
- [x] 数据解析和存储
- [x] 批量数据采集
- [x] 错误处理和日志记录
- [x] 使用示例和文档
- [ ] Web界面开发
- [ ] 数据可视化
