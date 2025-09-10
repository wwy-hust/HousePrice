#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL数据采集接口
提供简单的API接口来采集单个URL的房价数据
"""

import sys
import argparse
from data_collector import HousePriceDataCollector
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def collect_url_data(url, description=None, date=None, output_file=None):
    """
    采集单个URL的房价数据
    
    Args:
        url (str): 数据源URL
        description (str): 数据描述（可选）
        date (str): 数据日期（可选）
        output_file (str): 输出文件名（可选）
        
    Returns:
        bool: 采集是否成功
    """
    try:
        # 创建数据采集器
        collector = HousePriceDataCollector()
        
        # 如果没有提供描述，使用URL作为描述
        if not description:
            description = f"房价数据 - {url}"
        
        # 如果没有提供日期，使用当前日期
        if not date:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 采集数据
        success = collector.collect_single_url_data(url, description, date)
        
        if success:
            logger.info("✅ 数据采集成功！")
            return True
        else:
            logger.error("❌ 数据采集失败！")
            return False
            
    except Exception as e:
        logger.error(f"❌ 采集过程中发生错误: {e}")
        return False

def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='房价数据URL采集接口')
    parser.add_argument('url', help='要采集的数据源URL')
    parser.add_argument('-d', '--description', help='数据描述')
    parser.add_argument('-t', '--date', help='数据日期 (格式: YYYY-MM-DD)')
    parser.add_argument('-o', '--output', help='输出文件名')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 采集数据
    success = collect_url_data(
        url=args.url,
        description=args.description,
        date=args.date,
        output_file=args.output
    )
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
