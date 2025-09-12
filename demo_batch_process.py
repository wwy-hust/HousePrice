#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示批量处理功能 - 处理部分城市展示完整功能
"""

import json
import os
from datetime import datetime
from batch_process_all_cities import BatchProcessor

def demo_batch_process():
    """演示批量处理功能"""
    print("城市房价指数批量处理工具 - 演示版")
    print("=" * 60)
    print("将处理主要城市的8种房价指数类型")
    
    # 选择主要城市进行演示
    demo_cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安", "重庆"]
    
    print(f"演示城市: {', '.join(demo_cities)}")
    print(f"指数类型: 8种")
    
    # 创建自定义批量处理器
    class DemoProcessor(BatchProcessor):
        def get_all_cities(self):
            """重写获取城市方法，只返回演示城市"""
            return demo_cities
    
    try:
        # 创建演示处理器并开始处理
        processor = DemoProcessor(output_dir="demo_results")
        processor.process_all()
        
        print(f"\n✅ 演示处理完成！结果文件保存在 'demo_results' 目录中。")
        
        # 显示生成的文件
        print(f"\n生成的JSON文件:")
        for config in processor.index_configs:
            filepath = os.path.join("demo_results", config["filename"])
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"  ✓ {config['filename']} ({size:,} bytes)")
            else:
                print(f"  ✗ {config['filename']} (未生成)")
        
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_batch_process()
