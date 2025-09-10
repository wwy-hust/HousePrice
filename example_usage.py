#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL数据采集接口使用示例
演示如何使用数据采集功能
"""

from data_collector import HousePriceDataCollector
from url_collector_api import collect_url_data
import pandas as pd

def example_1_basic_usage():
    """示例1: 基本使用方法"""
    print("=" * 60)
    print("示例1: 基本使用方法")
    print("=" * 60)
    
    # 创建数据采集器
    collector = HousePriceDataCollector()
    
    # 采集单个URL的数据
    url = "https://www.stats.gov.cn/sj/zxfb/202507/t20250715_1960403.html"
    description = "2025年6月份70个大中城市商品住宅销售价格变动情况"
    date = "2025-07-15"
    
    print(f"正在采集数据...")
    print(f"URL: {url}")
    print(f"描述: {description}")
    print(f"日期: {date}")
    
    success = collector.collect_single_url_data(url, description, date)
    
    if success:
        print("✅ 数据采集成功！")
    else:
        print("❌ 数据采集失败！")

def example_2_batch_collection():
    """示例2: 批量采集"""
    print("\n" + "=" * 60)
    print("示例2: 批量采集多个URL")
    print("=" * 60)
    
    # 创建数据采集器
    collector = HousePriceDataCollector()
    
    # 加载URL列表
    url_df = collector.load_url_list()
    
    # 只采集前3个URL作为示例
    sample_urls = url_df.head(3)
    
    print(f"准备采集 {len(sample_urls)} 个URL的数据...")
    
    success_count = 0
    for index, row in sample_urls.iterrows():
        url = row['标题链接']
        description = row['标题']
        date = row['时间']
        
        print(f"\n正在采集第 {index + 1} 个URL...")
        print(f"描述: {description}")
        
        success = collector.collect_single_url_data(url, description, date)
        if success:
            success_count += 1
            print("✅ 采集成功")
        else:
            print("❌ 采集失败")
    
    print(f"\n批量采集完成！成功: {success_count}/{len(sample_urls)}")

def example_3_api_usage():
    """示例3: 使用API接口"""
    print("\n" + "=" * 60)
    print("示例3: 使用API接口")
    print("=" * 60)
    
    # 使用API接口采集数据
    url = "https://www.stats.gov.cn/sj/zxfb/202506/t20250616_1960163.html"
    description = "2025年5月份房价数据"
    date = "2025-06-16"
    
    print(f"使用API接口采集数据...")
    print(f"URL: {url}")
    
    success = collect_url_data(url, description, date)
    
    if success:
        print("✅ API采集成功！")
    else:
        print("❌ API采集失败！")

def example_4_data_analysis():
    """示例4: 数据分析示例"""
    print("\n" + "=" * 60)
    print("示例4: 数据分析示例")
    print("=" * 60)
    
    # 加载URL列表
    collector = HousePriceDataCollector()
    url_df = collector.load_url_list()
    
    print("URL列表信息:")
    print(f"总URL数量: {len(url_df)}")
    print(f"时间范围: {url_df['时间'].min()} 到 {url_df['时间'].max()}")
    
    # 按年份统计
    url_df['年份'] = pd.to_datetime(url_df['时间']).dt.year
    yearly_count = url_df['年份'].value_counts().sort_index()
    
    print("\n按年份统计:")
    for year, count in yearly_count.items():
        print(f"  {year}年: {count} 条数据")

def main():
    """主函数"""
    print("🏠 房价数据采集接口使用示例")
    print("本示例将演示如何使用数据采集功能")
    
    try:
        # 运行示例
        example_1_basic_usage()
        example_2_batch_collection()
        example_3_api_usage()
        example_4_data_analysis()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 运行示例时发生错误: {e}")

if __name__ == "__main__":
    main()
