#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国家统计局房价数据URL更新脚本
自动检查并更新HousePriceURL.csv中的70个大中城市商品住宅销售价格变动情况数据
"""

import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
import time
import sys
from urllib.parse import urljoin, urlparse

class HousePriceURLUpdater:
    def __init__(self, csv_file_path="HousePriceURL.csv"):
        self.csv_file_path = csv_file_path
        self.base_url = "https://www.stats.gov.cn"
        self.data_url = "https://www.stats.gov.cn/sj/zxfb/"
        self.existing_urls = set()
        self.existing_data = []
        
        # 请求头，模拟浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def load_existing_data(self):
        """读取现有的CSV文件数据"""
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                rows = list(reader)
                
                if rows:
                    # 跳过标题行
                    self.existing_data = rows
                    for row in rows[1:]:  # 跳过标题行
                        if len(row) >= 2:
                            self.existing_urls.add(row[1])  # URL列
                            
            print(f"已读取现有数据: {len(self.existing_urls)} 条记录")
            
        except FileNotFoundError:
            print("CSV文件不存在，将创建新文件")
            self.existing_data = [["标题", "标题链接", "时间"]]
        except Exception as e:
            print(f"读取CSV文件时出错: {e}")
            sys.exit(1)
    
    def get_page_content(self, url, max_retries=3):
        """获取网页内容，带重试机制"""
        for attempt in range(max_retries):
            try:
                print(f"正在访问: {url} (尝试 {attempt + 1}/{max_retries})")
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
                
            except requests.RequestException as e:
                print(f"请求失败 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 等待2秒后重试
                else:
                    print(f"无法访问 {url}")
                    return None
    
    def parse_date_from_text(self, text):
        """从文本中解析日期"""
        # 匹配各种日期格式
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2025-08-15
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',  # 2025年8月15日
            r'(\d{4})/(\d{1,2})/(\d{1,2})',  # 2025/8/15
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                year, month, day = match.groups()
                return f"{year}/{int(month)}/{int(day)}"
        
        return None
    
    def extract_house_price_data_from_page(self, html_content):
        """从单页HTML内容中提取70个大中城市商品住宅销售价格变动情况的数据"""
        soup = BeautifulSoup(html_content, 'html.parser')
        page_records = []
        
        # 查找包含房价数据的链接
        links = soup.find_all('a', href=True)
        
        for link in links:
            link_text = link.get_text(strip=True)
            href = link.get('href')
            
            # 检查是否包含关键词
            if "70个大中城市商品住宅销售价格变动情况" in link_text:
                # 构建完整URL - 处理相对路径
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('./'):
                    # 处理 ./202508/t20250815_1960781.html 格式
                    full_url = urljoin(self.data_url, href[2:])  # 去掉 ./
                else:
                    full_url = urljoin(self.base_url, href)
                
                # 从父元素的文本中提取日期
                date_str = None
                parent = link.parent
                if parent:
                    parent_text = parent.get_text()
                    # 查找日期模式 2025-08-15
                    date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', parent_text)
                    if date_match:
                        year, month, day = date_match.groups()
                        date_str = f"{year}/{int(month)}/{int(day)}"
                
                # 如果没找到日期，从链接文本中推断
                if not date_str:
                    date_match = re.search(r'(\d{4})年(\d{1,2})月', link_text)
                    if date_match:
                        year, month = date_match.groups()
                        # 根据历史数据，房价数据通常在次月中旬发布
                        if int(month) == 12:
                            date_str = f"{int(year)+1}/1/15"
                        else:
                            date_str = f"{year}/{int(month)+1}/15"
                
                # 如果仍然没有找到日期，使用当前日期作为fallback
                if not date_str:
                    date_str = datetime.now().strftime("%Y/%m/%d")
                
                record = {
                    'title': link_text,
                    'url': full_url,
                    'date': date_str
                }
                page_records.append(record)
        
        return page_records
    
    def extract_house_price_data(self):
        """从多页中提取房价数据，直到遇到已存在的条目"""
        all_new_records = []
        seen_urls = set()  # 用于去重
        page_num = 1
        max_pages = 10  # 最多检查10页，避免无限循环
        
        while page_num <= max_pages:
            # 构建页面URL
            if page_num == 1:
                page_url = self.data_url
            else:
                # 尝试不同的分页URL模式
                page_patterns = [
                    f"{self.data_url}index_{page_num}.html",
                    f"{self.data_url}?page={page_num}",
                    f"{self.base_url}/sj/zxfb/index_{page_num}.html"
                ]
                
                page_url = None
                for pattern in page_patterns:
                    test_content = self.get_page_content(pattern)
                    if test_content and len(test_content) > 1000:  # 简单检查页面是否有效
                        page_url = pattern
                        break
                
                if not page_url:
                    print(f"无法访问第{page_num}页，停止翻页")
                    break
            
            print(f"正在检查第{page_num}页: {page_url}")
            
            # 获取页面内容
            html_content = self.get_page_content(page_url)
            if not html_content:
                print(f"无法获取第{page_num}页内容，停止翻页")
                break
            
            # 提取当前页的房价数据
            page_records = self.extract_house_price_data_from_page(html_content)
            
            if not page_records:
                print(f"第{page_num}页未找到房价数据，停止翻页")
                break
            
            print(f"第{page_num}页找到 {len(page_records)} 个房价数据条目")
            
            # 检查是否有新数据，以及是否遇到已存在的条目
            found_existing = False
            page_new_records = []
            
            for record in page_records:
                # 检查URL是否已存在
                if record['url'] in self.existing_urls:
                    print(f"遇到已存在条目，停止翻页: {record['title']}")
                    found_existing = True
                    break
                
                # 检查是否在当前批次中重复
                if record['url'] not in seen_urls:
                    seen_urls.add(record['url'])
                    page_new_records.append(record)
                    print(f"发现新记录: {record['title']} -> {record['url']}")
            
            # 添加新记录
            all_new_records.extend(page_new_records)
            
            # 如果遇到已存在的条目，停止翻页
            if found_existing:
                break
            
            page_num += 1
            time.sleep(1)  # 避免请求过快
        
        print(f"翻页完成，共检查了 {page_num} 页，找到 {len(all_new_records)} 个新记录")
        return all_new_records
    
    def get_accurate_date_from_detail_page(self, url):
        """从详情页面获取准确的发布日期"""
        try:
            content = self.get_page_content(url)
            if not content:
                return None
                
            soup = BeautifulSoup(content, 'html.parser')
            
            # 寻找发布日期的常见位置
            date_selectors = [
                '.artical-info',
                '.article-info', 
                '.publish-time',
                '.time',
                '.date'
            ]
            
            for selector in date_selectors:
                date_element = soup.select_one(selector)
                if date_element:
                    date_text = date_element.get_text()
                    parsed_date = self.parse_date_from_text(date_text)
                    if parsed_date:
                        return parsed_date
            
            # 如果没找到，在整个页面中搜索日期模式
            page_text = soup.get_text()
            parsed_date = self.parse_date_from_text(page_text)
            if parsed_date:
                return parsed_date
                
        except Exception as e:
            print(f"获取详情页面日期时出错: {e}")
        
        return None
    
    def update_csv_file(self, new_records):
        """更新CSV文件"""
        if not new_records:
            print("没有新数据需要添加")
            return
        
        # 为新记录获取更准确的日期
        for record in new_records:
            print(f"获取详细日期: {record['title']}")
            accurate_date = self.get_accurate_date_from_detail_page(record['url'])
            if accurate_date:
                record['date'] = accurate_date
            time.sleep(1)  # 避免请求过快
        
        # 按日期排序（最新的在前面）
        new_records.sort(key=lambda x: datetime.strptime(x['date'], "%Y/%m/%d"), reverse=True)
        
        # 准备写入CSV的数据
        all_rows = []
        
        # 添加标题行
        all_rows.append(["标题", "标题链接", "时间"])
        
        # 添加新记录
        for record in new_records:
            all_rows.append([record['title'], record['url'], record['date']])
        
        # 添加现有记录（跳过标题行）
        if len(self.existing_data) > 1:
            all_rows.extend(self.existing_data[1:])
        
        # 写入CSV文件
        try:
            with open(self.csv_file_path, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(all_rows)
            
            print(f"成功更新CSV文件，添加了 {len(new_records)} 条新记录")
            for record in new_records:
                print(f"  - {record['title']} ({record['date']})")
                
        except Exception as e:
            print(f"写入CSV文件时出错: {e}")
    
    def run(self):
        """运行更新程序"""
        print("开始更新房价数据URL...")
        print("=" * 50)
        
        # 1. 读取现有数据
        self.load_existing_data()
        
        # 2. 从多页中提取新数据（包含翻页逻辑）
        new_records = self.extract_house_price_data()
        
        # 3. 更新CSV文件
        self.update_csv_file(new_records)
        
        print("=" * 50)
        print("更新完成!")

def main():
    updater = HousePriceURLUpdater()
    updater.run()

if __name__ == "__main__":
    main()
