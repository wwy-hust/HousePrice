#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试单个URL数据采集功能
"""

from data_collector import HousePriceDataCollector
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_single_url():
    """测试单个URL数据采集"""
    collector = HousePriceDataCollector()
    
    # 测试URL（使用Excel中的第一个URL）
    test_url = "http://www.stats.gov.cn/sj/zxfb/202312/t20231215_1945000.html"
    test_description = "2023年11月份70个大中城市商品住宅销售价格变动情况"
    test_date = "2023-11"
    
    print("=" * 60)
    print("开始测试单个URL数据采集")
    print("=" * 60)
    print(f"URL: {test_url}")
    print(f"描述: {test_description}")
    print(f"日期: {test_date}")
    print()
    
    try:
        # 采集数据
        success = collector.collect_single_url_data(test_url, test_description, test_date)
        
        if success:
            print("✅ 数据采集成功！")
            print("📁 数据已保存到 collected_data/ 目录")
        else:
            print("❌ 数据采集失败！")
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_single_url()
