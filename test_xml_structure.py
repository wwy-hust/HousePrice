#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试XML数据结构
验证采集的XML数据是否符合预期格式
"""

import xml.etree.ElementTree as ET
import os
import glob

def validate_xml_structure(xml_file):
    """
    验证XML文件结构
    
    Args:
        xml_file (str): XML文件路径
        
    Returns:
        dict: 验证结果
    """
    try:
        # 解析XML文件
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # 检查根元素
        if root.tag != 'house_price_data':
            return {'valid': False, 'error': '根元素标签不正确'}
        
        # 检查根元素属性
        required_attrs = ['source_url', 'description', 'date', 'collected_at']
        for attr in required_attrs:
            if attr not in root.attrib:
                return {'valid': False, 'error': f'缺少根元素属性: {attr}'}
        
        # 检查表格数量
        tables = root.findall('table')
        if len(tables) == 0:
            return {'valid': False, 'error': '未找到表格数据'}
        
        # 检查每个表格的结构
        table_info = []
        for i, table in enumerate(tables):
            table_data = {
                'index': table.get('index'),
                'rows': table.get('rows'),
                'columns': table.get('columns')
            }
            
            # 检查表格是否有列名和数据
            columns = table.find('columns')
            data = table.find('data')
            
            if columns is None:
                return {'valid': False, 'error': f'表格 {i+1} 缺少列名'}
            
            if data is None:
                return {'valid': False, 'error': f'表格 {i+1} 缺少数据'}
            
            # 统计列数和行数
            column_count = len(columns.findall('column'))
            row_count = len(data.findall('row'))
            
            table_data['actual_columns'] = column_count
            table_data['actual_rows'] = row_count
            
            table_info.append(table_data)
        
        return {
            'valid': True,
            'source_url': root.get('source_url'),
            'description': root.get('description'),
            'date': root.get('date'),
            'collected_at': root.get('collected_at'),
            'table_count': len(tables),
            'tables': table_info
        }
        
    except ET.ParseError as e:
        return {'valid': False, 'error': f'XML解析错误: {e}'}
    except Exception as e:
        return {'valid': False, 'error': f'验证过程中发生错误: {e}'}

def main():
    """主函数"""
    print("🔍 验证XML数据结构...")
    print("=" * 50)
    
    # 查找所有XML文件
    xml_files = glob.glob('collected_data/*.xml')
    
    if not xml_files:
        print("❌ 未找到XML文件")
        return
    
    # 验证每个XML文件
    for xml_file in xml_files:
        print(f"\n📄 验证文件: {xml_file}")
        result = validate_xml_structure(xml_file)
        
        if result['valid']:
            print("✅ XML结构验证通过")
            print(f"   数据源: {result['source_url']}")
            print(f"   描述: {result['description']}")
            print(f"   日期: {result['date']}")
            print(f"   采集时间: {result['collected_at']}")
            print(f"   表格数量: {result['table_count']}")
            
            for i, table in enumerate(result['tables']):
                print(f"   表格 {i+1}: {table['actual_rows']} 行 x {table['actual_columns']} 列")
        else:
            print(f"❌ XML结构验证失败: {result['error']}")

if __name__ == "__main__":
    main()
