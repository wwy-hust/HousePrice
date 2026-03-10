#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
房价数据可视化Web服务器
提供静态文件服务和数据API接口
"""

import os
import json
import mimetypes
import threading
import subprocess
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局更新任务状态
update_status = {
    'running': False,
    'logs': [],        # 完整日志列表，每行一条
    'step': '',
    'success': None,
    'error': '',
    'start_time': None,
    'end_time': None,
}
update_lock = threading.Lock()

def _push_log(line):
    with update_lock:
        update_status['logs'].append(line)

def run_update_task():
    """在后台线程中执行数据更新"""
    global update_status
    base_path = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(base_path, 'update_house_price_urls.py')

    with update_lock:
        update_status.update({
            'running': True,
            'logs': ['正在启动更新任务...'],
            'step': 'starting',
            'success': None,
            'error': '',
            'start_time': time.time(),
            'end_time': None,
        })

    try:
        import sys
        proc = subprocess.Popen(
            [sys.executable, script, '--auto-collect'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=base_path,
        )

        last_line = ''
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                last_line = line
                _push_log(line)
                logger.info(f'[update] {line}')

        proc.wait()
        success = proc.returncode == 0

        with update_lock:
            update_status['running'] = False
            update_status['success'] = success
            update_status['end_time'] = time.time()
            if success:
                update_status['step'] = 'done'
                update_status['logs'].append('数据更新完成！')
            else:
                update_status['step'] = 'error'
                update_status['error'] = f'脚本退出码: {proc.returncode}，最后输出: {last_line}'
                update_status['logs'].append(f'更新失败：{update_status["error"]}')

    except Exception as e:
        with update_lock:
            update_status['running'] = False
            update_status['success'] = False
            update_status['step'] = 'error'
            update_status['error'] = str(e)
            update_status['logs'].append(f'出错: {e}')
            update_status['end_time'] = time.time()
        logger.error(f'更新任务异常: {e}')


class HousePriceHandler(BaseHTTPRequestHandler):
    """房价数据HTTP请求处理器"""
    
    def __init__(self, *args, **kwargs):
        # 设置基础路径
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.web_path = os.path.join(self.base_path, 'web')
        self.results_path = os.path.join(self.base_path, 'results')
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            # API请求处理
            if path.startswith('/api/'):
                self.handle_api_request(path)
            # 静态文件处理
            else:
                self.handle_static_request(path)
                
        except Exception as e:
            logger.error(f"处理请求时发生错误: {e}")
            self.send_error(500, "Internal Server Error")
    
    def handle_api_request(self, path):
        """处理API请求"""
        if path.startswith('/api/data/'):
            # 数据文件请求
            filename = path.replace('/api/data/', '')
            self.serve_data_file(filename)
        elif path == '/api/cities':
            # 城市列表请求
            self.serve_cities_list()
        elif path.startswith('/api/city/'):
            # 单个城市数据请求
            from urllib.parse import unquote
            city_info = path.replace('/api/city/', '').split('/')
            if len(city_info) >= 2:
                city_name = unquote(city_info[0])  # URL解码
                data_type = city_info[1]
                self.serve_city_data(city_name, data_type)
            else:
                self.send_error(400, "Invalid City Request Format")
        elif path == '/api/update':
            self.handle_update_trigger()
        elif path == '/api/update/status':
            self.handle_update_status()
        else:
            self.send_error(404, "API Not Found")
    
    def serve_data_file(self, filename):
        """提供数据文件"""
        # 安全检查：只允许访问指定的JSON文件
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
            self.send_error(403, "Access Forbidden")
            return
        
        file_path = os.path.join(self.results_path, filename)
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            self.send_error(404, "Data File Not Found")
            return
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        logger.info(f"开始提供数据文件: {filename} (大小: {file_size/1024/1024:.1f}MB)")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"JSON文件解析成功: {filename}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'max-age=300')  # 缓存5分钟
            # 添加文件大小头
            response_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))  # 压缩JSON
            self.send_header('Content-Length', str(len(response_data.encode('utf-8'))))
            self.end_headers()
            
            self.wfile.write(response_data.encode('utf-8'))
            
            logger.info(f"成功提供数据文件: {filename} (响应大小: {len(response_data)/1024/1024:.1f}MB)")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误 {filename}: {e}")
            self.send_error(500, "Invalid JSON Format")
        except Exception as e:
            logger.error(f"读取文件错误 {filename}: {e}")
            self.send_error(500, "File Read Error")
    
    def handle_update_trigger(self):
        """触发数据更新任务"""
        with update_lock:
            if update_status['running']:
                resp = {'ok': False, 'message': '已有更新任务正在执行，请稍候'}
            else:
                t = threading.Thread(target=run_update_task, daemon=True)
                t.start()
                resp = {'ok': True, 'message': '更新任务已启动'}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))

    def handle_update_status(self):
        """返回当前更新状态，支持 ?offset=N 只返回新增日志"""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            offset = int(params.get('offset', ['0'])[0])
        except (ValueError, IndexError):
            offset = 0

        with update_lock:
            logs = update_status['logs']
            new_logs = logs[offset:]
            snap = {
                'running': update_status['running'],
                'step': update_status['step'],
                'success': update_status['success'],
                'error': update_status['error'],
                'total_logs': len(logs),
                'new_logs': new_logs,
            }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(snap, ensure_ascii=False).encode('utf-8'))

    def serve_cities_list(self):
        """提供城市列表"""
        cities = [
            "三亚", "上海", "东莞", "中山", "丹东", "乌鲁木齐", "兰州", "北京", "南京", "南宁",
            "南昌", "南通", "厦门", "唐山", "哈尔滨", "呼和浩特", "大理", "大连", "天津", "太原",
            "宁波", "安庆", "宜昌", "常德", "广州", "廊坊", "徐州", "惠州", "成都", "扬州",
            "无锡", "昆明", "杭州", "桂林", "武汉", "泉州", "济南", "济宁", "海口", "深圳",
            "温州", "湖州", "湘潭", "烟台", "牡丹江", "珠海", "福州", "秦皇岛", "绵阳", "肇庆",
            "西宁", "西安", "贵阳", "赣州", "遵义", "郑州", "重庆", "金华", "锦州", "长春",
            "长沙", "韶关", "青岛", "韩城", "包头", "北海", "平顶山", "银川", "丽水", "石家庄"
        ]
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response_data = json.dumps({
            'cities': sorted(cities),
            'total': len(cities)
        }, ensure_ascii=False, indent=2)
        self.wfile.write(response_data.encode('utf-8'))
    
    def serve_city_data(self, city_name, data_type):
        """提供单个城市的数据"""
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
            self.send_error(400, "Invalid Data Type")
            return
        
        filename = data_type_map[data_type]
        file_path = os.path.join(self.results_path, filename)
        
        if not os.path.exists(file_path):
            logger.error(f"数据文件不存在: {file_path}")
            self.send_error(404, "Data File Not Found")
            return
        
        try:
            logger.info(f"加载城市数据: {city_name} - {data_type}")
            
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
                self.send_error(404, f"City '{city_name}' Not Found")
                return
            
            # 构造响应数据（只包含元数据和指定城市的数据）
            response_data_obj = {
                'index_type': full_data.get('index_type'),
                'house_type': full_data.get('house_type'),
                'area_type': full_data.get('area_type'),
                'generated_at': full_data.get('generated_at'),
                'city_data': city_data
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'max-age=300')
            self.end_headers()
            
            response_data = json.dumps(response_data_obj, ensure_ascii=False, separators=(',', ':'))
            self.wfile.write(response_data.encode('utf-8'))
            
            logger.info(f"成功提供城市数据: {city_name} - {data_type} (大小: {len(response_data)/1024:.1f}KB)")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误 {filename}: {e}")
            self.send_error(500, "Invalid JSON Format")
        except Exception as e:
            logger.error(f"处理城市数据错误: {e}")
            self.send_error(500, "Internal Server Error")
    
    def handle_static_request(self, path):
        """处理静态文件请求"""
        # 根路径重定向到index.html
        if path == '/' or path == '':
            path = '/index.html'
        
        # 移除开头的斜杠
        if path.startswith('/'):
            path = path[1:]
        
        file_path = os.path.join(self.web_path, path)
        
        # 安全检查：确保文件在web目录内
        if not os.path.commonpath([file_path, self.web_path]) == self.web_path:
            self.send_error(403, "Access Forbidden")
            return
        
        if not os.path.exists(file_path):
            self.send_error(404, "File Not Found")
            return
        
        if os.path.isdir(file_path):
            # 如果是目录，查找index.html
            index_path = os.path.join(file_path, 'index.html')
            if os.path.exists(index_path):
                file_path = index_path
            else:
                self.send_error(404, "Index File Not Found")
                return
        
        try:
            # 确定MIME类型
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            # 为文本文件添加UTF-8编码
            if mime_type.startswith('text/') or mime_type == 'application/javascript':
                mime_type += '; charset=utf-8'
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(len(content)))
            
            # 为静态资源添加缓存头
            if path.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico')):
                self.send_header('Cache-Control', 'max-age=86400')  # 缓存1天
            
            self.end_headers()
            self.wfile.write(content)
            
            logger.info(f"成功提供静态文件: {path}")
            
        except Exception as e:
            logger.error(f"提供静态文件错误 {path}: {e}")
            self.send_error(500, "File Read Error")
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        logger.info(f"{self.client_address[0]} - {format % args}")

def run_server(host='localhost', port=8000):
    """运行Web服务器"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, HousePriceHandler)
    
    logger.info(f"房价数据可视化服务器启动")
    logger.info(f"服务地址: http://{host}:{port}")
    logger.info(f"按 Ctrl+C 停止服务器")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务器...")
        httpd.server_close()
        logger.info("服务器已关闭")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='房价数据可视化Web服务器')
    parser.add_argument('--host', default='localhost', help='服务器主机地址 (默认: localhost)')
    parser.add_argument('--port', type=int, default=8000, help='服务器端口 (默认: 8000)')
    
    args = parser.parse_args()
    
    # 检查必要的目录和文件
    base_path = os.path.dirname(os.path.abspath(__file__))
    web_path = os.path.join(base_path, 'web')
    results_path = os.path.join(base_path, 'results')
    
    if not os.path.exists(web_path):
        logger.error(f"Web目录不存在: {web_path}")
        exit(1)
    
    if not os.path.exists(results_path):
        logger.error(f"Results目录不存在: {results_path}")
        exit(1)
    
    # 检查关键文件
    index_file = os.path.join(web_path, 'index.html')
    if not os.path.exists(index_file):
        logger.error(f"index.html文件不存在: {index_file}")
        exit(1)
    
    run_server(args.host, args.port)
