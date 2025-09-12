#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
房价数据可视化系统 WSGI 应用
用于Apache mod_wsgi部署
"""

import os
import sys
import logging
from urllib.parse import urlparse, parse_qs

# 添加项目路径到Python路径
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# 导入应用处理器
from web_server import HousePriceHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/apache2/house-price-wsgi.log')
    ]
)
logger = logging.getLogger(__name__)

class WSGIApp:
    """WSGI应用包装器"""
    
    def __init__(self):
        self.base_path = project_path
        self.web_path = os.path.join(self.base_path, 'web')
        self.results_path = os.path.join(self.base_path, 'results')
        logger.info(f"WSGI应用初始化完成，项目路径: {self.base_path}")
    
    def __call__(self, environ, start_response):
        """WSGI应用入口点"""
        try:
            # 解析请求
            method = environ.get('REQUEST_METHOD', 'GET')
            path = environ.get('PATH_INFO', '/')
            query_string = environ.get('QUERY_STRING', '')
            
            logger.info(f"处理请求: {method} {path}")
            
            # 只处理API请求
            if not path.startswith('/api/'):
                # 非API请求返回404，让Apache处理静态文件
                status = '404 Not Found'
                headers = [('Content-Type', 'text/plain')]
                start_response(status, headers)
                return [b'API endpoint not found']
            
            # 创建模拟的请求处理器
            handler = MockHandler(environ, self.base_path, self.web_path, self.results_path)
            
            if method == 'GET':
                response_data, status, headers = handler.handle_get_request(path)
            else:
                # 其他HTTP方法
                status = '405 Method Not Allowed'
                headers = [('Content-Type', 'text/plain')]
                response_data = b'Method not allowed'
            
            start_response(status, headers)
            return [response_data]
            
        except Exception as e:
            logger.error(f"WSGI处理错误: {e}")
            status = '500 Internal Server Error'
            headers = [('Content-Type', 'text/plain')]
            start_response(status, headers)
            return [b'Internal Server Error']

class MockHandler:
    """模拟HTTP请求处理器，用于WSGI环境"""
    
    def __init__(self, environ, base_path, web_path, results_path):
        self.environ = environ
        self.base_path = base_path
        self.web_path = web_path
        self.results_path = results_path
    
    def handle_get_request(self, path):
        """处理GET请求"""
        try:
            if path.startswith('/api/data/'):
                # 数据文件请求
                filename = path.replace('/api/data/', '')
                return self.serve_data_file(filename)
            elif path == '/api/cities':
                # 城市列表请求
                return self.serve_cities_list()
            elif path.startswith('/api/city/'):
                # 单个城市数据请求
                from urllib.parse import unquote
                city_info = path.replace('/api/city/', '').split('/')
                if len(city_info) >= 2:
                    city_name = unquote(city_info[0])
                    data_type = city_info[1]
                    return self.serve_city_data(city_name, data_type)
                else:
                    return b'Invalid City Request Format', '400 Bad Request', [('Content-Type', 'text/plain')]
            else:
                return b'API Not Found', '404 Not Found', [('Content-Type', 'text/plain')]
                
        except Exception as e:
            logger.error(f"处理GET请求错误: {e}")
            return b'Internal Server Error', '500 Internal Server Error', [('Content-Type', 'text/plain')]
    
    def serve_data_file(self, filename):
        """提供数据文件"""
        import json
        
        # 安全检查
        allowed_files = [
            'new_house_basic_index.json',
            'used_house_basic_index.json',
            'new_house_classified_90_below.json',
            'new_house_classified_90_144.json',
            'new_house_classified_144_above.json',
            'used_house_classified_90_below.json',
            'used_house_classified_90_144.json',
            'used_house_classified_144_above.json',
            'summary_report.json'
        ]
        
        if filename not in allowed_files:
            logger.warning(f"访问被拒绝的文件: {filename}")
            return b'Access Forbidden', '403 Forbidden', [('Content-Type', 'text/plain')]
        
        file_path = os.path.join(self.results_path, filename)
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return b'Data File Not Found', '404 Not Found', [('Content-Type', 'text/plain')]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            response_data = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            headers = [
                ('Content-Type', 'application/json; charset=utf-8'),
                ('Access-Control-Allow-Origin', '*'),
                ('Cache-Control', 'max-age=300'),
                ('Content-Length', str(len(response_data)))
            ]
            
            logger.info(f"成功提供数据文件: {filename}")
            return response_data, '200 OK', headers
            
        except Exception as e:
            logger.error(f"读取文件错误 {filename}: {e}")
            return b'File Read Error', '500 Internal Server Error', [('Content-Type', 'text/plain')]
    
    def serve_cities_list(self):
        """提供城市列表"""
        import json
        
        cities = [
            "三亚", "上海", "东莞", "中山", "丹东", "乌鲁木齐", "兰州", "北京", "南京", "南宁",
            "南昌", "南通", "厦门", "唐山", "哈尔滨", "呼和浩特", "大理", "大连", "天津", "太原",
            "宁波", "安庆", "宜昌", "常德", "广州", "廊坊", "徐州", "惠州", "成都", "扬州",
            "无锡", "昆明", "杭州", "桂林", "武汉", "泉州", "济南", "济宁", "海口", "深圳",
            "温州", "湖州", "湘潭", "烟台", "牡丹江", "珠海", "福州", "秦皇岛", "绵阳", "肇庆",
            "西宁", "西安", "贵阳", "赣州", "遵义", "郑州", "重庆", "金华", "锦州", "长春",
            "长沙", "韶关", "青岛", "韩城", "包头", "北海", "平顶山", "银川", "丽水", "石家庄"
        ]
        
        response_data_obj = {
            'cities': sorted(cities),
            'total': len(cities)
        }
        
        response_data = json.dumps(response_data_obj, ensure_ascii=False, indent=2).encode('utf-8')
        headers = [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Access-Control-Allow-Origin', '*'),
            ('Content-Length', str(len(response_data)))
        ]
        
        return response_data, '200 OK', headers
    
    def serve_city_data(self, city_name, data_type):
        """提供单个城市的数据"""
        import json
        
        # 数据类型映射
        data_type_map = {
            'new_house_basic': 'new_house_basic_index.json',
            'used_house_basic': 'used_house_basic_index.json',
            'new_house_classified_90_below': 'new_house_classified_90_below.json',
            'new_house_classified_90_144': 'new_house_classified_90_144.json',
            'new_house_classified_144_above': 'new_house_classified_144_above.json',
            'used_house_classified_90_below': 'used_house_classified_90_below.json',
            'used_house_classified_90_144': 'used_house_classified_90_144.json',
            'used_house_classified_144_above': 'used_house_classified_144_above.json'
        }
        
        if data_type not in data_type_map:
            logger.warning(f"无效的数据类型: {data_type}")
            return b'Invalid Data Type', '400 Bad Request', [('Content-Type', 'text/plain')]
        
        filename = data_type_map[data_type]
        file_path = os.path.join(self.results_path, filename)
        
        if not os.path.exists(file_path):
            logger.error(f"数据文件不存在: {file_path}")
            return b'Data File Not Found', '404 Not Found', [('Content-Type', 'text/plain')]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
            
            # 查找指定城市的数据
            city_data = None
            for city in full_data.get('cities', []):
                if city.get('city') == city_name:
                    city_data = city
                    break
            
            if not city_data:
                logger.warning(f"未找到城市数据: {city_name}")
                return f"City '{city_name}' Not Found".encode('utf-8'), '404 Not Found', [('Content-Type', 'text/plain')]
            
            # 构造响应数据
            response_data_obj = {
                'index_type': full_data.get('index_type'),
                'house_type': full_data.get('house_type'),
                'area_type': full_data.get('area_type'),
                'generated_at': full_data.get('generated_at'),
                'city_data': city_data
            }
            
            response_data = json.dumps(response_data_obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            headers = [
                ('Content-Type', 'application/json; charset=utf-8'),
                ('Access-Control-Allow-Origin', '*'),
                ('Cache-Control', 'max-age=300'),
                ('Content-Length', str(len(response_data)))
            ]
            
            logger.info(f"成功提供城市数据: {city_name} - {data_type}")
            return response_data, '200 OK', headers
            
        except Exception as e:
            logger.error(f"处理城市数据错误: {e}")
            return b'Internal Server Error', '500 Internal Server Error', [('Content-Type', 'text/plain')]

# 创建WSGI应用实例
application = WSGIApp()

if __name__ == '__main__':
    # 测试模式
    from wsgiref.simple_server import make_server
    httpd = make_server('localhost', 8001, application)
    print("WSGI测试服务器运行在 http://localhost:8001")
    httpd.serve_forever()
