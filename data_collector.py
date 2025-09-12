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
from io import StringIO

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
        import re
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = []
        
        # 查找所有表格
        table_elements = soup.find_all('table')
        logger.info(f"找到 {len(table_elements)} 个表格")
        
        for i, table in enumerate(table_elements):
            try:
                # 查找表格前的标题
                table_title = ""
                table_name = ""
                
                # 向前查找包含"表X："格式的标题
                current = table
                while current and not table_title:
                    current = current.find_previous()
                    if current and hasattr(current, 'get_text'):
                        text = current.get_text()
                        # 匹配"表X：XXXXX指数"格式
                        match = re.search(r'表(\d+)[:：](.+?指数)', text)
                        if match:
                            table_number = match.group(1)
                            table_content = match.group(2)
                            table_title = f"表{table_number}：{table_content}"
                            # 提取表格名称（去掉"表X："前缀）
                            table_name = table_content
                            break
                
                # 使用pandas解析表格
                df = pd.read_html(StringIO(str(table)), encoding='utf-8')[0]
                
                # 清理数据
                df = df.dropna(how='all')  # 删除全空行
                df = df.fillna('')  # 填充空值
                
                # 清理城市名称中的空格（处理所有可能包含城市名的列）
                for col in df.columns:
                    if df[col].dtype == 'object':  # 如果是字符串列
                        # 检查是否包含城市名（通过检查是否有中文字符和空格）
                        sample_values = df[col].dropna().astype(str).head(10)
                        has_chinese_with_space = any(
                            any('\u4e00' <= char <= '\u9fff' for char in str(val)) and ' ' in str(val)
                            for val in sample_values
                        )
                        if has_chinese_with_space:
                            df[col] = df[col].astype(str).str.replace(' ', '', regex=False)
                
                tables.append({
                    'table_index': i + 1,
                    'table_title': table_title,
                    'table_name': table_name,
                    'data': df,
                    'columns': df.columns.tolist(),
                    'shape': df.shape
                })
                
                logger.info(f"表格 {i + 1}: {df.shape[0]} 行 x {df.shape[1]} 列")
                if table_title:
                    logger.info(f"表格标题: {table_title}")
                
            except Exception as e:
                logger.warning(f"解析表格 {i + 1} 失败: {e}")
                continue
        
        return tables
    
    def _is_header_row(self, row):
        """
        判断是否为表头行
        表头行的特征：不包含城市名称
        
        Args:
            row (pandas.Series): 数据行
            
        Returns:
            bool: 是否为表头行
        """
        # 定义一些常见的中国城市名称
        cities = [
            '北京', '上海', '天津', '重庆', '广州', '深圳', '杭州', '南京', '武汉', '成都',
            '西安', '郑州', '青岛', '大连', '宁波', '厦门', '济南', '沈阳', '长春', '哈尔滨',
            '石家庄', '太原', '呼和浩特', '兰州', '西宁', '银川', '乌鲁木齐', '拉萨', '昆明', '贵阳',
            '南宁', '海口', '三亚', '福州', '合肥', '南昌', '长沙', '苏州', '无锡', '常州',
            '徐州', '温州', '嘉兴', '金华', '台州', '绍兴', '湖州', '丽水', '衢州', '舟山',
            '唐山', '秦皇岛', '邯郸', '保定', '张家口', '承德', '廊坊', '沧州', '衡水', '邢台',
            '大同', '阳泉', '长治', '晋城', '朔州', '晋中', '运城', '忻州', '临汾', '吕梁',
            '包头', '乌海', '赤峰', '通辽', '鄂尔多斯', '呼伦贝尔', '巴彦淖尔', '乌兰察布',
            '锡林郭勒盟', '兴安盟', '阿拉善盟', '鞍山', '抚顺', '本溪', '丹东', '锦州', '营口',
            '阜新', '辽阳', '盘锦', '铁岭', '朝阳', '葫芦岛', '吉林', '四平', '辽源', '通化',
            '白山', '松原', '白城', '延边', '齐齐哈尔', '鸡西', '鹤岗', '双鸭山', '大庆', '伊春',
            '佳木斯', '七台河', '牡丹江', '黑河', '绥化', '大兴安岭', '蚌埠', '芜湖', '马鞍山',
            '淮南', '淮北', '铜陵', '安庆', '黄山', '滁州', '阜阳', '宿州', '六安', '亳州',
            '池州', '宣城', '莆田', '三明', '泉州', '漳州', '南平', '龙岩', '宁德', '景德镇',
            '萍乡', '九江', '新余', '鹰潭', '赣州', '吉安', '宜春', '抚州', '上饶', '株洲',
            '湘潭', '衡阳', '邵阳', '岳阳', '常德', '张家界', '益阳', '郴州', '永州', '怀化',
            '娄底', '湘西', '韶关', '珠海', '汕头', '佛山', '江门', '湛江', '茂名', '肇庆',
            '惠州', '梅州', '汕尾', '河源', '阳江', '清远', '东莞', '中山', '潮州', '揭阳',
            '云浮', '柳州', '桂林', '梧州', '北海', '防城港', '钦州', '贵港', '玉林', '百色',
            '贺州', '河池', '来宾', '崇左', '遵义', '六盘水', '安顺', '毕节', '铜仁', '黔西南',
            '黔东南', '黔南', '曲靖', '玉溪', '保山', '昭通', '丽江', '普洱', '临沧', '楚雄',
            '红河', '文山', '西双版纳', '大理', '德宏', '怒江', '迪庆'
        ]
        
        # 检查第一列是否包含城市名称（处理空格问题）
        first_value = str(row.iloc[0]).strip()
        first_value_no_space = first_value.replace(' ', '')  # 去除空格后再匹配
        
        # 如果第一列的值是城市名称（去除空格后匹配），则不是表头行
        if first_value_no_space in cities:
            return False
            
        # 如果第一列包含"城市"、"环比"、"同比"等表头关键词，则是表头行
        header_keywords = ['城市', '环比', '同比', '平均', '上月', '上年', '=100']
        if any(keyword in first_value for keyword in header_keywords):
            return True
            
        # 默认情况：如果不包含任何中文城市名，可能是表头行
        return not any(city in first_value_no_space for city in cities)
    
    def _merge_tables_by_name(self, tables):
        """
        根据表格名称合并同名表格
        
        Args:
            tables (list): 表格数据列表
            
        Returns:
            list: 合并后的表格列表
        """
        merged_tables = {}
        
        for table_info in tables:
            table_name = table_info.get('table_name', '')
            
            if table_name in merged_tables:
                # 合并到已存在的表格
                existing_table = merged_tables[table_name]
                
                # 合并数据：只保留一份表头，合并数据行
                existing_df = existing_table['data']
                new_df = table_info['data']
                
                # 分离表头行和数据行
                existing_head_indices = []
                existing_data_indices = []
                new_data_indices = []
                
                for idx, row in existing_df.iterrows():
                    if self._is_header_row(row):
                        existing_head_indices.append(idx)
                    else:
                        existing_data_indices.append(idx)
                
                for idx, row in new_df.iterrows():
                    if not self._is_header_row(row):  # 只添加数据行，跳过表头行
                        new_data_indices.append(idx)
                
                # 构建合并后的DataFrame
                merged_parts = []
                
                # 添加表头行（只从第一个表格中取）
                if existing_head_indices:
                    head_df = existing_df.iloc[existing_head_indices].copy()
                    merged_parts.append(head_df)
                
                # 添加第一个表格的数据行
                if existing_data_indices:
                    data_df1 = existing_df.iloc[existing_data_indices].copy()
                    merged_parts.append(data_df1)
                
                # 添加新表格的数据行
                if new_data_indices:
                    data_df2 = new_df.iloc[new_data_indices].copy()
                    merged_parts.append(data_df2)
                
                # 合并所有部分
                if merged_parts:
                    merged_df = pd.concat(merged_parts, ignore_index=True)
                    
                    # 更新表格信息
                    existing_table['data'] = merged_df
                    existing_table['shape'] = merged_df.shape
                    
                    logger.info(f"合并表格: {table_name} - 新尺寸: {merged_df.shape}")
            else:
                # 第一次遇到这个表名，直接添加
                merged_tables[table_name] = table_info.copy()
        
        # 重新分配表格索引
        merged_list = []
        for idx, (table_name, table_info) in enumerate(merged_tables.items(), 1):
            table_info['table_index'] = idx
            merged_list.append(table_info)
        
        logger.info(f"表格合并完成: 原始 {len(tables)} 个表格，合并后 {len(merged_list)} 个表格")
        return merged_list
    
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
        
        # 合并同名表格
        merged_tables = self._merge_tables_by_name(tables)
        
        # 添加表格数据
        for table_info in merged_tables:
            table_elem = ET.SubElement(root, 'table')
            table_elem.set('index', str(table_info['table_index']))
            table_elem.set('rows', str(table_info['shape'][0]))
            table_elem.set('columns', str(table_info['shape'][1]))
            # 添加表格标题和名称属性
            if table_info.get('table_title'):
                table_elem.set('title', table_info['table_title'])
            if table_info.get('table_name'):
                table_elem.set('name', table_info['table_name'])
            
            # 分离表头行和数据行
            df = table_info['data']
            head_rows = []
            data_rows = []
            
            for idx, row in df.iterrows():
                # 判断是否为表头行：检查第一列是否包含城市名称
                is_header_row = self._is_header_row(row)
                
                if is_header_row:
                    head_rows.append((idx, row))
                else:
                    data_rows.append((idx, row))
            
            # 检查是否为表1或表2，需要特殊处理
            table_name = table_info.get('table_name', '')
            is_table_1_or_2 = ('新建商品住宅销售价格指数' in table_name and '分类' not in table_name) or \
                              ('二手住宅销售价格指数' in table_name and '分类' not in table_name)
            
            if is_table_1_or_2:
                # 特殊处理表1和表2
                self._add_table_1_2_structure(table_elem, head_rows, data_rows)
            else:
                # 普通处理表3和表4
                self._add_normal_table_structure(table_elem, head_rows, data_rows)
        
        return root
    
    def _add_table_1_2_structure(self, table_elem, head_rows, data_rows):
        """
        为表1和表2添加特殊的XML结构
        - 自适应处理6列或8列数据
        - 6列：城市1,环比1,同比1,城市2,环比2,同比2 → 拆分为两行，每行3列
        - 8列：城市1,环比1,同比1,定基1,城市2,环比2,同比2,定基2 → 拆分为两行，每行4列
        """
        # 检测数据列数以确定拆分方式
        cols_per_city = 3  # 默认3列（城市、环比、同比）
        if data_rows:
            first_data_row = data_rows[0][1]
            total_cols = len(first_data_row)
            if total_cols >= 8:
                cols_per_city = 4  # 8列：每个城市4列（城市、环比、同比、定基）
            elif total_cols >= 6:
                cols_per_city = 3  # 6列：每个城市3列（城市、环比、同比）
            else:
                cols_per_city = total_cols // 2  # 其他情况平均分配
        
        # 添加表头部分（合并row0和row1）
        if head_rows:
            head_section = ET.SubElement(table_elem, 'head')
            
            # 合并表头行
            if len(head_rows) >= 2:
                merged_head_row = self._merge_head_rows(head_rows[0][1], head_rows[1][1], cols_per_city)
                head_row_elem = ET.SubElement(head_section, 'row')
                head_row_elem.set('index', '0')
                
                # 根据检测到的列数保留相应的cell
                for col_index in range(min(cols_per_city, len(merged_head_row))):
                    cell_elem = ET.SubElement(head_row_elem, 'cell')
                    cell_elem.set('column', str(col_index))
                    cell_elem.text = merged_head_row[col_index]
            elif len(head_rows) == 1:
                # 只有一行表头的情况
                head_row_elem = ET.SubElement(head_section, 'row')
                head_row_elem.set('index', '0')
                
                col_count = 0
                for col_name, value in head_rows[0][1].items():
                    if col_count >= cols_per_city:
                        break
                    cell_elem = ET.SubElement(head_row_elem, 'cell')
                    cell_elem.set('column', str(col_count))
                    cell_elem.text = str(value)
                    col_count += 1
        
        # 添加数据部分（自适应拆分每行）
        if data_rows:
            data_elem = ET.SubElement(table_elem, 'data')
            new_row_index = 0
            
            for original_idx, row in data_rows:
                row_values = [str(value) for value in row.values]
                total_cols = len(row_values)
                
                # 根据总列数判断每个城市的列数，并确保能整除2（因为有两个城市）
                if total_cols >= cols_per_city * 2:
                    # 第一行：前cols_per_city个cell（城市1的数据）
                    row_elem_1 = ET.SubElement(data_elem, 'row')
                    row_elem_1.set('index', str(new_row_index))
                    
                    for i in range(cols_per_city):
                        cell_elem = ET.SubElement(row_elem_1, 'cell')
                        cell_elem.set('column', str(i))
                        cell_elem.text = row_values[i]
                    
                    new_row_index += 1
                    
                    # 第二行：后cols_per_city个cell（城市2的数据）
                    row_elem_2 = ET.SubElement(data_elem, 'row')
                    row_elem_2.set('index', str(new_row_index))
                    
                    for i in range(cols_per_city):
                        cell_elem = ET.SubElement(row_elem_2, 'cell')
                        cell_elem.set('column', str(i))
                        cell_elem.text = row_values[i + cols_per_city]
                    
                    new_row_index += 1
    
    def _merge_head_rows(self, row1, row2, cols_per_city=3):
        """
        合并两行表头数据
        
        Args:
            row1 (pandas.Series): 第一行数据
            row2 (pandas.Series): 第二行数据
            cols_per_city (int): 每个城市的列数
            
        Returns:
            list: 合并后的表头内容
        """
        merged_row = []
        row1_values = [str(value) for value in row1.values]
        row2_values = [str(value) for value in row2.values]
        
        max_cols = min(len(row1_values), len(row2_values), cols_per_city)
        
        for i in range(max_cols):
            val1 = row1_values[i].strip()
            val2 = row2_values[i].strip()
            
            if val1 == val2:
                # 内容相同，只保留一份
                merged_row.append(val1)
            else:
                # 内容不同，拼接（用括号分隔）
                if val2:
                    merged_row.append(f"{val1}({val2})")
                else:
                    merged_row.append(val1)
        
        return merged_row
    
    def _merge_multiple_head_rows(self, rows):
        """
        合并多行表头数据（用于表3和表4）
        
        Args:
            rows (list): 多行pandas.Series数据
            
        Returns:
            list: 合并后的表头内容
        """
        merged_row = []
        
        if not rows:
            return merged_row
        
        # 获取所有行的值
        all_rows_values = []
        max_cols = 0
        for row in rows:
            row_values = [str(value).strip() for value in row.values]
            all_rows_values.append(row_values)
            max_cols = max(max_cols, len(row_values))
        
        # 按列合并
        for col_index in range(max_cols):
            col_values = []
            for row_values in all_rows_values:
                if col_index < len(row_values):
                    col_values.append(row_values[col_index])
                else:
                    col_values.append("")
            
            # 去重并拼接
            unique_values = []
            for val in col_values:
                if val and val not in unique_values:
                    unique_values.append(val)
            
            # 合并同列的内容
            if len(unique_values) == 1:
                merged_row.append(unique_values[0])
            elif len(unique_values) > 1:
                # 按照逻辑顺序拼接：面积类型 + 指标类型 + 计算基准
                merged_row.append("(".join(unique_values) + ")" * (len(unique_values) - 1))
            else:
                merged_row.append("")
        
        return merged_row
    
    def _add_normal_table_structure(self, table_elem, head_rows, data_rows):
        """
        为表3和表4添加优化的XML结构
        - head合并多行为一行
        - data行索引从0开始重新编号
        """
        # 添加表头部分（合并多行为一行）
        if head_rows:
            head_section = ET.SubElement(table_elem, 'head')
            
            # 合并多行表头
            if len(head_rows) >= 3:
                merged_head_row = self._merge_multiple_head_rows([row[1] for row in head_rows[:3]])
                head_row_elem = ET.SubElement(head_section, 'row')
                head_row_elem.set('index', '0')
                
                for col_index in range(len(merged_head_row)):
                    cell_elem = ET.SubElement(head_row_elem, 'cell')
                    cell_elem.set('column', str(col_index))
                    cell_elem.text = merged_head_row[col_index]
            else:
                # 处理少于3行表头的情况
                for idx, row in head_rows:
                    head_row_elem = ET.SubElement(head_section, 'row')
                    head_row_elem.set('index', str(idx))
                    
                    col_index = 0
                    for col_name, value in row.items():
                        cell_elem = ET.SubElement(head_row_elem, 'cell')
                        cell_elem.set('column', str(col_index))
                        cell_elem.text = str(value)
                        col_index += 1
        
        # 添加数据部分（重新编号从0开始）
        if data_rows:
            data_elem = ET.SubElement(table_elem, 'data')
            new_row_index = 0
            
            for original_idx, row in data_rows:
                row_elem = ET.SubElement(data_elem, 'row')
                row_elem.set('index', str(new_row_index))
                
                col_index = 0
                for col_name, value in row.items():
                    cell_elem = ET.SubElement(row_elem, 'cell')
                    cell_elem.set('column', str(col_index))
                    cell_elem.text = str(value)
                    col_index += 1
                
                new_row_index += 1
    
    def _format_date_for_filename(self, date_str):
        """
        格式化日期字符串用于文件名，确保月份是两位数
        
        Args:
            date_str (str): 原始日期字符串，格式如 "2024/2/23" 或 "2024-2-23"
            
        Returns:
            str: 格式化后的日期字符串，格式如 "2024_02_23"
        """
        import re
        
        # 处理不同的日期分隔符
        date_str = date_str.replace('/', '_').replace('-', '_')
        
        # 使用正则表达式匹配日期格式 YYYY_M_DD 或 YYYY_MM_DD
        pattern = r'(\d{4})_(\d{1,2})_(\d{1,2})'
        match = re.match(pattern, date_str)
        
        if match:
            year, month, day = match.groups()
            # 确保月份和日期都是两位数
            month = month.zfill(2)
            day = day.zfill(2)
            return f"{year}_{month}_{day}"
        else:
            # 如果格式不匹配，直接返回处理过分隔符的字符串
            return date_str
    
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
            
            # 生成文件名，确保月份是两位数格式
            safe_date = self._format_date_for_filename(date)
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
        # for idx in range(1):
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
    # collector = HousePriceDataCollector()
    # url = "https://www.stats.gov.cn/sj/zxfb/202402/t20240223_1947806.html"
    # description = "2024年1月份70个大中城市商品住宅销售价格变动情况"
    # date = "2024/2/23"
    # success = collector.collect_single_url_data(url, description, date)
    main()
