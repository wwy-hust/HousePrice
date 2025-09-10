#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
房价数据采集模块
从国家统计局网站获取房价数据并存储为XML格式
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import time
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HousePriceDataCollector:
    """房价数据采集器"""
    
    def __init__(self):
        self.session = requests.Session()
        # 设置请求头，模拟浏览器访问
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 创建数据存储目录
        self.data_dir = 'collected_data'
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def fetch_page_content(self, url, max_retries=3):
        """
        获取网页内容
        
        Args:
            url (str): 目标URL
            max_retries (int): 最大重试次数
            
        Returns:
            str: 网页HTML内容
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"正在获取页面内容: {url} (尝试 {attempt + 1}/{max_retries})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
            except requests.RequestException as e:
                logger.warning(f"获取页面失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    logger.error(f"获取页面最终失败: {url}")
                    raise
    
    def parse_tables_from_html(self, html_content):
        """
        从HTML内容中解析表格数据
        
        Args:
            html_content (str): HTML内容
            
        Returns:
            list: 包含四个表格数据的列表
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = []
        
        # 查找所有表格
        table_elements = soup.find_all('table')
        logger.info(f"找到 {len(table_elements)} 个表格")
        
        for i, table in enumerate(table_elements):
            try:
                # 使用pandas解析表格
                df = pd.read_html(str(table), encoding='utf-8')[0]
                
                # 清理数据
                df = df.dropna(how='all')  # 删除全空行
                df = df.fillna('')  # 填充空值
                
                tables.append({
                    'table_index': i + 1,
                    'data': df,
                    'columns': df.columns.tolist(),
                    'shape': df.shape
                })
                
                logger.info(f"表格 {i + 1}: {df.shape[0]} 行 x {df.shape[1]} 列")
                
            except Exception as e:
                logger.warning(f"解析表格 {i + 1} 失败: {e}")
                continue
        
        return tables
    
    def create_xml_structure(self, url, description, date, tables):
        """
        创建XML数据结构
        
        Args:
            url (str): 数据源URL
            description (str): 数据描述
            date (str): 数据日期
            tables (list): 表格数据列表
            
        Returns:
            xml.etree.ElementTree.Element: XML根元素
        """
        # 创建根元素
        root = ET.Element('house_price_data')
        root.set('source_url', url)
        root.set('description', description)
        root.set('date', date)
        root.set('collected_at', datetime.now().isoformat())
        
        # 添加表格数据
        for table_info in tables:
            table_elem = ET.SubElement(root, 'table')
            table_elem.set('index', str(table_info['table_index']))
            table_elem.set('rows', str(table_info['shape'][0]))
            table_elem.set('columns', str(table_info['shape'][1]))
            
            # 添加列名
            columns_elem = ET.SubElement(table_elem, 'columns')
            for col in table_info['columns']:
                col_elem = ET.SubElement(columns_elem, 'column')
                col_elem.text = str(col)
            
            # 添加数据行
            data_elem = ET.SubElement(table_elem, 'data')
            df = table_info['data']
            
            for idx, row in df.iterrows():
                row_elem = ET.SubElement(data_elem, 'row')
                row_elem.set('index', str(idx))
                
                for col_name, value in row.items():
                    cell_elem = ET.SubElement(row_elem, 'cell')
                    cell_elem.set('column', str(col_name))
                    cell_elem.text = str(value)
        
        return root
    
    def save_xml_data(self, xml_root, filename):
        """
        保存XML数据到文件
        
        Args:
            xml_root (xml.etree.ElementTree.Element): XML根元素
            filename (str): 文件名
        """
        # 格式化XML
        rough_string = ET.tostring(xml_root, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding='utf-8')
        
        # 保存文件
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(pretty_xml)
        
        logger.info(f"XML数据已保存到: {filepath}")
    
    def collect_single_url_data(self, url, description, date):
        """
        从单个URL采集数据
        
        Args:
            url (str): 数据源URL
            description (str): 数据描述
            date (str): 数据日期
            
        Returns:
            bool: 采集是否成功
        """
        try:
            # 获取网页内容
            html_content = self.fetch_page_content(url)
            
            # 解析表格数据
            tables = self.parse_tables_from_html(html_content)
            
            if not tables:
                logger.warning(f"未找到表格数据: {url}")
                return False
            
            # 创建XML结构
            xml_root = self.create_xml_structure(url, description, date, tables)
            
            # 生成文件名
            safe_date = date.replace('-', '_')
            filename = f"house_price_data_{safe_date}.xml"
            
            # 保存XML数据
            self.save_xml_data(xml_root, filename)
            
            logger.info(f"成功采集数据: {description} ({date})")
            return True
            
        except Exception as e:
            logger.error(f"采集数据失败: {url} - {e}")
            return False
    
    def load_url_list(self, csv_file='HousePriceURL.csv'):
        """
        从CSV文件加载URL列表
        
        Args:
            csv_file (str): CSV文件路径
            
        Returns:
            pandas.DataFrame: URL列表数据
        """
        try:
            df = pd.read_csv(csv_file)
            logger.info(f"加载了 {len(df)} 个URL")
            return df
        except Exception as e:
            logger.error(f"加载URL列表失败: {e}")
            raise

def main():
    """主函数 - 测试单个URL数据采集"""
    collector = HousePriceDataCollector()
    
    # 加载URL列表
    url_df = collector.load_url_list()
    print(url_df)
    
    if len(url_df) > 0:
        # 测试第一个URL
        for idx in range(len(url_df)):
            url_row = url_df.iloc[idx]
            print(url_row)
            url = url_row['标题链接']
            description = url_row['标题']
            date = url_row['时间']
        
            print(f"采集URL: {url}")
            print(f"描述: {description}")
            print(f"日期: {date}")
            
            # 采集数据
            success = collector.collect_single_url_data(url, description, date)
            
            if success:
                print("✅ 数据采集成功！")
            else:
                print("❌ 数据采集失败！")

if __name__ == "__main__":
    main()
