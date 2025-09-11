#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
城市房价指数数据处理脚本
处理某个城市的新建商品住宅销售价格指数数据
按时间排序提取环比和同比数据，并计算实际递推值
"""

import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional


class PriceIndexCalculationEngine:
    """房价指数计算引擎 - 通用计算和矫正逻辑"""
    
    def __init__(self):
        """初始化计算引擎"""
        pass
    
    def calculate_actual_values(self, price_data: List[Dict], base_value: float = 100.0) -> List[Dict]:
        """
        计算实际递推值
        处理方式：环比数值先减去100，再用减过的值作为环比，计算当月的实际值
        
        Args:
            price_data: 价格数据列表，每个元素包含date, month_on_month, year_on_year等字段
            base_value: 基准值（第一个月的实际值）
            
        Returns:
            包含实际值的数据列表
        """
        if not price_data:
            return []
        
        result = []
        current_value = base_value
        
        for i, data in enumerate(price_data):
            # 环比数值先减去100，得到增长率
            growth_rate = (data['month_on_month'] - 100) / 100
            
            # 计算当月实际值
            if i == 0:
                # 第一个月使用基准值
                actual_value = base_value
            else:
                # 后续月份基于前一个月的值计算
                actual_value = current_value * (1 + growth_rate)
            
            result.append({
                'date': data['date'],
                'month_on_month': data['month_on_month'],
                'year_on_year': data['year_on_year'],
                'growth_rate': growth_rate,
                'actual_value': actual_value,
                'filepath': data.get('filepath', '')
            })
            
            current_value = actual_value
        
        return result
    
    def calculate_corrected_values(self, price_data: List[Dict], base_value: float = 100.0, 
                                 max_iterations: int = 200, tolerance: float = 0.001) -> List[Dict]:
        """
        计算矫正后的实际值
        通过环比和同比的交叉验证，调整实际值以满足统计局数据的精度要求
        
        Args:
            price_data: 价格数据列表
            base_value: 基准值（第一个月的实际值）
            max_iterations: 最大迭代次数
            tolerance: 收敛容差
            
        Returns:
            包含矫正后实际值的数据列表
        """
        if not price_data:
            return []
        
        # 首先进行基础的环比递推计算
        result = self.calculate_actual_values(price_data, base_value)
        
        # 进行多轮精确矫正
        for iteration in range(max_iterations):
            corrections_made = 0
            max_adjustment = 0
            
            # 第一阶段：基于环比和同比约束的粗调
            for i in range(len(result)):
                current_data = result[i]
                original_value = current_data['actual_value']
                
                # 计算理想的实际值
                ideal_value = self._calculate_ideal_value(result, i)
                
                if ideal_value is not None:
                    # 计算调整量
                    adjustment = ideal_value - original_value
                    max_adjustment = max(max_adjustment, abs(adjustment))
                    
                    # 动态阻尼因子：随迭代次数减小
                    damping_factor = max(0.1, 0.8 * (1 - iteration / max_iterations))
                    new_value = original_value + adjustment * damping_factor
                    
                    # 更新实际值
                    result[i]['actual_value'] = new_value
                    result[i]['corrected'] = True
                    corrections_made += 1
            
            # 第二阶段：精确匹配调整
            if iteration > 10:  # 在粗调后进行精确调整
                self._precise_matching_adjustment(result)
            
            # 更新连锁效应
            self._update_all_chain_effects(result)
            
            # 检查收敛条件
            if max_adjustment < tolerance:
                break
        
        # 计算最终的验证指标
        for i, data in enumerate(result):
            verification = self._verify_data_consistency(result, i)
            data.update(verification)
        
        # 最终强制匹配阶段：多轮匹配直到满足条件
        max_force_iterations = 5
        for force_iter in range(max_force_iterations):
            # 验证当前状态
            for i, data in enumerate(result):
                verification = self._verify_data_consistency(result, i)
                data.update(verification)
            
            # 统计不匹配数量
            mom_mismatches = sum(1 for d in result if not d.get('mom_match', True))
            yoy_mismatches = sum(1 for d in result if not d.get('yoy_match', True))
            total_mismatches = mom_mismatches + yoy_mismatches
            
            if total_mismatches <= 2:
                break  # 达到目标，退出
            
            # 执行强制匹配
            self._force_final_matching(result)
        
        # 最终验证
        for i, data in enumerate(result):
            verification = self._verify_data_consistency(result, i)
            data.update(verification)
        
        return result
    
    def _calculate_ideal_value(self, result: List[Dict], index: int) -> Optional[float]:
        """
        计算理想的实际值
        基于环比和同比约束条件
        
        Args:
            result: 当前结果列表
            index: 当前数据点索引
            
        Returns:
            理想的实际值，如果无法计算则返回None
        """
        current_data = result[index]
        target_mom = current_data['month_on_month']
        target_yoy = current_data['year_on_year']
        
        ideal_value = None
        
        # 基于环比约束
        if index > 0:
            prev_value = result[index - 1]['actual_value']
            # 目标环比：current_value / prev_value * 100 = target_mom
            ideal_from_mom = prev_value * target_mom / 100
            ideal_value = ideal_from_mom
        
        # 基于同比约束（如果有12个月前的数据）
        if index >= 12:
            prev_year_value = result[index - 12]['actual_value']
            # 目标同比：current_value / prev_year_value * 100 = target_yoy
            ideal_from_yoy = prev_year_value * target_yoy / 100
            
            if ideal_value is not None:
                # 如果两个约束都存在，取加权平均
                # 给同比更高的权重，因为它通常更准确
                ideal_value = ideal_value * 0.3 + ideal_from_yoy * 0.7
            else:
                ideal_value = ideal_from_yoy
        
        return ideal_value
    
    def _precise_matching_adjustment(self, result: List[Dict]):
        """
        精确匹配调整
        针对不匹配的数据点进行微调，确保匹配数量最大化
        
        Args:
            result: 结果列表
        """
        for i in range(len(result)):
            current_data = result[i]
            actual_value = current_data['actual_value']
            
            # 检查环比匹配
            if i > 0:
                prev_value = result[i - 1]['actual_value']
                calculated_mom = (actual_value / prev_value) * 100
                target_mom = current_data['month_on_month']
                
                # 如果环比不匹配，进行微调
                if abs(round(calculated_mom, 1) - target_mom) >= 0.05:
                    # 计算需要的精确值
                    precise_value = prev_value * target_mom / 100
                    # 小幅调整
                    adjustment = (precise_value - actual_value) * 0.3
                    result[i]['actual_value'] += adjustment
            
            # 检查同比匹配
            if i >= 12:
                prev_year_value = result[i - 12]['actual_value']
                calculated_yoy = (actual_value / prev_year_value) * 100
                target_yoy = current_data['year_on_year']
                
                # 如果同比不匹配，进行微调
                if abs(round(calculated_yoy, 1) - target_yoy) >= 0.05:
                    # 计算需要的精确值
                    precise_value = prev_year_value * target_yoy / 100
                    # 小幅调整，权重更高
                    adjustment = (precise_value - actual_value) * 0.5
                    result[i]['actual_value'] += adjustment
    
    def _update_all_chain_effects(self, result: List[Dict]):
        """
        更新所有连锁效应
        确保整体数据的一致性
        
        Args:
            result: 结果列表
        """
        # 从第二个数据点开始，确保环比一致性
        for i in range(1, len(result)):
            if i > 0:
                prev_value = result[i - 1]['actual_value']
                current_value = result[i]['actual_value']
                target_mom = result[i]['month_on_month']
                
                # 计算基于环比的理想值
                ideal_from_mom = prev_value * target_mom / 100
                
                # 如果当前值与理想值差异较大，进行小幅调整
                if abs(current_value - ideal_from_mom) > 0.1:
                    # 保留原值的70%，调整30%
                    result[i]['actual_value'] = current_value * 0.7 + ideal_from_mom * 0.3
    
    def _force_final_matching(self, result: List[Dict]):
        """
        强制最终匹配
        使用贪心算法确保不匹配的数据点数量少于2个
        
        Args:
            result: 结果列表
        """
        # 统计所有不匹配的数据点
        all_mismatches = []
        
        for i in range(len(result)):
            mismatch_info = {'index': i, 'type': [], 'priority': 0}
            
            # 检查环比匹配
            if i > 0:
                prev_value = result[i - 1]['actual_value']
                actual_value = result[i]['actual_value']
                calculated_mom = (actual_value / prev_value) * 100
                target_mom = result[i]['month_on_month']
                
                if abs(round(calculated_mom, 1) - target_mom) >= 0.05:
                    mismatch_info['type'].append('mom')
                    mismatch_info['priority'] += 1
            
            # 检查同比匹配
            if i >= 12:
                prev_year_value = result[i - 12]['actual_value']
                actual_value = result[i]['actual_value']
                calculated_yoy = (actual_value / prev_year_value) * 100
                target_yoy = result[i]['year_on_year']
                
                if abs(round(calculated_yoy, 1) - target_yoy) >= 0.05:
                    mismatch_info['type'].append('yoy')
                    mismatch_info['priority'] += 2  # 同比优先级更高
            
            if mismatch_info['type']:
                all_mismatches.append(mismatch_info)
        
        # 按优先级排序，优先修正同比不匹配
        all_mismatches.sort(key=lambda x: x['priority'], reverse=True)
        
        # 强制修正，直到不匹配数量≤2
        while len(all_mismatches) > 2:
            mismatch = all_mismatches.pop(0)  # 取出优先级最高的
            i = mismatch['index']
            
            # 根据不匹配类型进行精确修正
            if 'yoy' in mismatch['type'] and i >= 12:
                # 优先修正同比
                prev_year_value = result[i - 12]['actual_value']
                target_yoy = result[i]['year_on_year']
                result[i]['actual_value'] = prev_year_value * target_yoy / 100
                
            elif 'mom' in mismatch['type'] and i > 0:
                # 修正环比
                prev_value = result[i - 1]['actual_value']
                target_mom = result[i]['month_on_month']
                result[i]['actual_value'] = prev_value * target_mom / 100
        
        # 重新验证剩余的不匹配点，确保没有新的不匹配产生
        remaining_mismatches = []
        for i in range(len(result)):
            has_mismatch = False
            
            # 检查环比
            if i > 0:
                prev_value = result[i - 1]['actual_value']
                actual_value = result[i]['actual_value']
                calculated_mom = (actual_value / prev_value) * 100
                target_mom = result[i]['month_on_month']
                if abs(round(calculated_mom, 1) - target_mom) >= 0.05:
                    has_mismatch = True
            
            # 检查同比
            if i >= 12:
                prev_year_value = result[i - 12]['actual_value']
                actual_value = result[i]['actual_value']
                calculated_yoy = (actual_value / prev_year_value) * 100
                target_yoy = result[i]['year_on_year']
                if abs(round(calculated_yoy, 1) - target_yoy) >= 0.05:
                    has_mismatch = True
            
            if has_mismatch:
                remaining_mismatches.append(i)
        
        # 如果仍然超过2个不匹配，采用最激进的修正策略
        while len(remaining_mismatches) > 2:
            i = remaining_mismatches.pop(0)
            
            # 优先基于同比进行修正（因为同比通常更准确）
            if i >= 12:
                prev_year_value = result[i - 12]['actual_value']
                target_yoy = result[i]['year_on_year']
                result[i]['actual_value'] = prev_year_value * target_yoy / 100
            elif i > 0:
                # 如果没有同比，则基于环比修正
                prev_value = result[i - 1]['actual_value']
                target_mom = result[i]['month_on_month']
                result[i]['actual_value'] = prev_value * target_mom / 100
    
    def _verify_data_consistency(self, result: List[Dict], index: int) -> Dict:
        """
        验证数据一致性
        计算基于实际值的环比和同比，与原始数据对比
        
        Args:
            result: 结果列表
            index: 当前数据点索引
            
        Returns:
            验证结果字典
        """
        current_data = result[index]
        actual_value = current_data['actual_value']
        
        verification = {
            'calculated_mom': None,
            'calculated_yoy': None,
            'mom_error': None,
            'yoy_error': None,
            'mom_match': True,  # 默认为True，只有在不匹配时才设为False
            'yoy_match': True   # 默认为True，只有在不匹配时才设为False
        }
        
        # 计算环比
        if index > 0:
            prev_value = result[index - 1]['actual_value']
            calculated_mom = (actual_value / prev_value) * 100
            verification['calculated_mom'] = calculated_mom
            
            # 计算环比误差
            original_mom = current_data['month_on_month']
            verification['mom_error'] = abs(calculated_mom - original_mom)
            
            # 检查四舍五入后是否匹配（更严格的匹配标准）
            verification['mom_match'] = abs(round(calculated_mom, 1) - original_mom) < 0.05
        
        # 计算同比
        if index >= 12:
            prev_year_value = result[index - 12]['actual_value']
            calculated_yoy = (actual_value / prev_year_value) * 100
            verification['calculated_yoy'] = calculated_yoy
            
            # 计算同比误差
            original_yoy = current_data['year_on_year']
            verification['yoy_error'] = abs(calculated_yoy - original_yoy)
            
            # 检查四舍五入后是否匹配（更严格的匹配标准）
            verification['yoy_match'] = abs(round(calculated_yoy, 1) - original_yoy) < 0.05
        
        return verification


class CityPriceProcessor:
    """城市房价指数处理器"""
    
    def __init__(self, data_dir: str = "collected_data"):
        """
        初始化处理器
        
        Args:
            data_dir: 数据文件目录
        """
        self.data_dir = data_dir
        self.data_files = self._get_sorted_data_files()
        self.calculation_engine = PriceIndexCalculationEngine()
    
    def _get_sorted_data_files(self) -> List[str]:
        """
        获取按时间排序的数据文件列表
        
        Returns:
            排序后的文件路径列表
        """
        files = []
        if not os.path.exists(self.data_dir):
            print(f"错误：数据目录 {self.data_dir} 不存在")
            return files
        
        # 获取所有XML文件
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.xml') and filename.startswith('house_price_data_'):
                filepath = os.path.join(self.data_dir, filename)
                files.append(filepath)
        
        # 按文件名排序（文件名包含日期）
        files.sort()
        return files
    
    def _extract_date_from_filename(self, filepath: str) -> Optional[str]:
        """
        从文件名提取日期
        
        Args:
            filepath: 文件路径
            
        Returns:
            日期字符串 (YYYY-MM格式)
        """
        filename = os.path.basename(filepath)
        match = re.search(r'house_price_data_(\d{4})_(\d{2})_\d{2}\.xml', filename)
        if match:
            year, month = match.groups()
            return f"{year}-{month}"
        return None
    
    def _parse_xml_file(self, filepath: str, house_type: str = "新建商品住宅") -> Optional[Dict]:
        """
        解析XML文件
        
        Args:
            filepath: XML文件路径
            house_type: 房屋类型，"新建商品住宅" 或 "二手住宅"
            
        Returns:
            解析后的数据字典
        """
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # 查找指定类型的销售价格指数表格
            table = None
            search_keyword = f"{house_type}销售价格指数"
            
            for t in root.findall('.//table'):
                title = t.get('title', '')
                name = t.get('name', '')
                if search_keyword in title or search_keyword in name:
                    table = t
                    break
            
            if table is None:
                print(f"警告：在文件 {filepath} 中未找到{house_type}销售价格指数表格")
                return None
            
            # 解析数据
            data = {}
            data_rows = table.find('.//data')
            if data_rows is not None:
                for row in data_rows.findall('row'):
                    cells = row.findall('cell')
                    if len(cells) >= 3:
                        city = cells[0].text.strip() if cells[0].text else ""
                        month_on_month = cells[1].text.strip() if cells[1].text else ""
                        year_on_year = cells[2].text.strip() if cells[2].text else ""
                        
                        if city and month_on_month and year_on_year:
                            try:
                                data[city] = {
                                    'month_on_month': float(month_on_month),
                                    'year_on_year': float(year_on_year)
                                }
                            except ValueError:
                                continue
            
            return data
            
        except ET.ParseError as e:
            print(f"错误：解析XML文件 {filepath} 失败: {e}")
            return None
        except Exception as e:
            print(f"错误：处理文件 {filepath} 时发生异常: {e}")
            return None
    
    def _parse_classified_xml_file(self, filepath: str, house_type: str = "新建商品住宅", area_type: str = "90m2及以下") -> Optional[Dict]:
        """
        解析XML文件中的分类指数数据
        
        Args:
            filepath: XML文件路径
            house_type: 房屋类型，"新建商品住宅" 或 "二手住宅"
            area_type: 面积类型，"90m2及以下", "90-144m2", "144m2以上"
            
        Returns:
            解析后的数据字典
        """
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # 查找指定类型的销售价格分类指数表格
            table = None
            search_keyword = f"{house_type}销售价格分类指数"
            
            for t in root.findall('.//table'):
                title = t.get('title', '')
                name = t.get('name', '')
                if search_keyword in title or search_keyword in name:
                    table = t
                    break
            
            if table is None:
                print(f"警告：在文件 {filepath} 中未找到{house_type}销售价格分类指数表格")
                return None
            
            # 解析表头，找到对应面积类型的列索引
            head_row = table.find('.//head/row')
            if head_row is None:
                print(f"警告：在文件 {filepath} 中未找到表头信息")
                return None
            
            # 查找面积类型对应的环比和同比列索引
            mom_col_index = None
            yoy_col_index = None
            
            cells = head_row.findall('cell')
            for i, cell in enumerate(cells):
                cell_text = cell.text.strip() if cell.text else ""
                if area_type in cell_text and "环比" in cell_text:
                    mom_col_index = i
                elif area_type in cell_text and "同比" in cell_text:
                    yoy_col_index = i
            
            if mom_col_index is None or yoy_col_index is None:
                print(f"警告：在文件 {filepath} 中未找到{area_type}的环比和同比数据列")
                return None
            
            # 解析数据
            data = {}
            data_rows = table.find('.//data')
            if data_rows is not None:
                for row in data_rows.findall('row'):
                    cells = row.findall('cell')
                    if len(cells) > max(mom_col_index, yoy_col_index):
                        city = cells[0].text.strip() if cells[0].text else ""
                        month_on_month_text = cells[mom_col_index].text.strip() if cells[mom_col_index].text else ""
                        year_on_year_text = cells[yoy_col_index].text.strip() if cells[yoy_col_index].text else ""
                        
                        if city and month_on_month_text and year_on_year_text:
                            try:
                                data[city] = {
                                    'month_on_month': float(month_on_month_text),
                                    'year_on_year': float(year_on_year_text)
                                }
                            except ValueError:
                                continue
            
            return data
            
        except ET.ParseError as e:
            print(f"错误：解析XML文件 {filepath} 失败: {e}")
            return None
        except Exception as e:
            print(f"错误：处理文件 {filepath} 时发生异常: {e}")
            return None
    
    def extract_city_data(self, city_name: str, house_type: str = "新建商品住宅") -> List[Dict]:
        """
        提取指定城市的数据
        
        Args:
            city_name: 城市名称
            house_type: 房屋类型，"新建商品住宅" 或 "二手住宅"
            
        Returns:
            按时间排序的城市数据列表
        """
        city_data = []
        
        for filepath in self.data_files:
            date = self._extract_date_from_filename(filepath)
            if not date:
                continue
                
            xml_data = self._parse_xml_file(filepath, house_type)
            if not xml_data or city_name not in xml_data:
                continue
            
            city_info = xml_data[city_name]
            city_data.append({
                'date': date,
                'month_on_month': city_info['month_on_month'],
                'year_on_year': city_info['year_on_year'],
                'filepath': filepath
            })
        
        return city_data
    
    def extract_city_classified_data(self, city_name: str, house_type: str = "新建商品住宅", 
                                   area_type: str = "90m2及以下") -> List[Dict]:
        """
        提取指定城市的分类指数数据
        
        Args:
            city_name: 城市名称
            house_type: 房屋类型，"新建商品住宅" 或 "二手住宅"
            area_type: 面积类型，"90m2及以下", "90-144m2", "144m2以上"
            
        Returns:
            按时间排序的城市分类数据列表
        """
        city_data = []
        
        for filepath in self.data_files:
            date = self._extract_date_from_filename(filepath)
            if not date:
                continue
                
            xml_data = self._parse_classified_xml_file(filepath, house_type, area_type)
            if not xml_data or city_name not in xml_data:
                continue
            
            city_info = xml_data[city_name]
            city_data.append({
                'date': date,
                'month_on_month': city_info['month_on_month'],
                'year_on_year': city_info['year_on_year'],
                'filepath': filepath
            })
        
        return city_data
    
    def calculate_actual_values(self, city_data: List[Dict], base_value: float = 100.0) -> List[Dict]:
        """
        计算实际递推值
        使用通用计算引擎进行计算
        
        Args:
            city_data: 城市数据列表
            base_value: 基准值（第一个月的实际值）
            
        Returns:
            包含实际值的数据列表
        """
        return self.calculation_engine.calculate_actual_values(city_data, base_value)
    
    def calculate_corrected_values(self, city_data: List[Dict], base_value: float = 100.0, 
                                 max_iterations: int = 200, tolerance: float = 0.001) -> List[Dict]:
        """
        计算矫正后的实际值
        使用通用计算引擎进行矫正计算
        
        Args:
            city_data: 城市数据列表
            base_value: 基准值（第一个月的实际值）
            max_iterations: 最大迭代次数
            tolerance: 收敛容差
            
        Returns:
            包含矫正后实际值的数据列表
        """
        return self.calculation_engine.calculate_corrected_values(city_data, base_value, max_iterations, tolerance)
    
    def process_city_classified(self, city_name: str, house_type: str = "新建商品住宅", 
                              area_type: str = "90m2及以下", base_value: float = 100.0):
        """
        处理指定城市的分类指数数据并输出结果
        
        Args:
            city_name: 城市名称
            house_type: 房屋类型，"新建商品住宅" 或 "二手住宅"
            area_type: 面积类型，"90m2及以下", "90-144m2", "144m2以上"
            base_value: 基准值
        """
        # 提取城市分类数据
        city_data = self.extract_city_classified_data(city_name, house_type, area_type)
        
        if not city_data:
            print(f"未找到城市 '{city_name}' 的{house_type} {area_type} 分类数据")
            return
        
        # 计算基础实际值
        processed_data = self.calculate_actual_values(city_data, base_value)
        
        # 计算矫正后的值
        corrected_data = self.calculate_corrected_values(city_data, base_value)
        
        # 打印对比结果
        self.print_classified_comparison_results(city_name, city_data, processed_data, corrected_data, house_type, area_type)
    
    def print_results(self, city_name: str, city_data: List[Dict], processed_data: List[Dict], 
                     corrected_data: List[Dict] = None, house_type: str = "新建商品住宅"):
        """
        打印处理结果
        
        Args:
            city_name: 城市名称
            city_data: 原始数据
            processed_data: 处理后的数据
            corrected_data: 矫正后的数据（可选）
            house_type: 房屋类型
        """
        print("=" * 100)
        print(f"城市{house_type}销售价格指数数据处理结果 - {city_name}")
        print("=" * 100)
        
        if not city_data:
            print(f"未找到城市 '{city_name}' 的数据")
            return
        
        print(f"\n数据时间范围: {city_data[0]['date']} 至 {city_data[-1]['date']}")
        print(f"数据记录数量: {len(city_data)} 条")
        
        print("\n" + "=" * 100)
        print("原始数据 (按时间排序)")
        print("=" * 100)
        print(f"{'日期':<12} {'环比':<10} {'同比':<10} {'数据文件'}")
        print("-" * 100)
        
        for data in city_data:
            filename = os.path.basename(data['filepath'])
            print(f"{data['date']:<12} {data['month_on_month']:<10.1f} {data['year_on_year']:<10.1f} {filename}")
        
        # 如果有矫正数据，显示矫正结果
        if corrected_data:
            self._print_corrected_results(corrected_data)
        else:
            self._print_basic_results(processed_data)
    
    def _print_basic_results(self, processed_data: List[Dict]):
        """打印基础处理结果"""
        print("\n" + "=" * 100)
        print("处理后的数据 (递推计算实际值)")
        print("=" * 100)
        print(f"{'日期':<12} {'环比':<10} {'同比':<10} {'增长率(%)':<12} {'实际值':<12}")
        print("-" * 100)
        
        for data in processed_data:
            print(f"{data['date']:<12} {data['month_on_month']:<10.1f} {data['year_on_year']:<10.1f} "
                  f"{data['growth_rate']*100:<11.2f} {data['actual_value']:<12.2f}")
        
        # 输出统计信息
        if processed_data:
            max_value = max(d['actual_value'] for d in processed_data)
            min_value = min(d['actual_value'] for d in processed_data)
            final_value = processed_data[-1]['actual_value']
            total_growth = ((final_value - 100) / 100) * 100
            
            print("\n" + "=" * 100)
            print("统计信息")
            print("=" * 100)
            print(f"最高值: {max_value:.2f}")
            print(f"最低值: {min_value:.2f}")
            print(f"最终值: {final_value:.2f}")
            print(f"总体增长: {total_growth:.2f}%")
    
    def _print_corrected_results(self, corrected_data: List[Dict]):
        """打印矫正后的结果"""
        print("\n" + "=" * 100)
        print("矫正后的数据 (环比同比交叉验证)")
        print("=" * 100)
        print(f"{'日期':<10} {'原环比':<8} {'原同比':<8} {'矫正值':<10} {'计算环比':<10} {'计算同比':<10} {'环比匹配':<8} {'同比匹配':<8}")
        print("-" * 100)
        
        for data in corrected_data:
            mom_match = "✓" if data.get('mom_match', False) else "✗"
            yoy_match = "✓" if data.get('yoy_match', False) else "✗"
            
            calc_mom = data.get('calculated_mom')
            calc_yoy = data.get('calculated_yoy')
            
            # 处理None值
            calc_mom_str = f"{calc_mom:.1f}" if calc_mom is not None else "-"
            calc_yoy_str = f"{calc_yoy:.1f}" if calc_yoy is not None else "-"
            
            print(f"{data['date']:<10} {data['month_on_month']:<8.1f} {data['year_on_year']:<8.1f} "
                  f"{data['actual_value']:<10.2f} {calc_mom_str:<10} {calc_yoy_str:<10} "
                  f"{mom_match:<8} {yoy_match:<8}")
        
        # 输出矫正统计信息
        self._print_correction_statistics(corrected_data)
    
    def _print_correction_statistics(self, corrected_data: List[Dict]):
        """打印矫正统计信息"""
        if not corrected_data:
            return
        
        print("\n" + "=" * 100)
        print("矫正统计信息")
        print("=" * 100)
        
        # 基本统计
        max_value = max(d['actual_value'] for d in corrected_data)
        min_value = min(d['actual_value'] for d in corrected_data)
        final_value = corrected_data[-1]['actual_value']
        total_growth = ((final_value - 100) / 100) * 100
        
        print(f"最高值: {max_value:.2f}")
        print(f"最低值: {min_value:.2f}")
        print(f"最终值: {final_value:.2f}")
        print(f"总体增长: {total_growth:.2f}%")
        
        # 验证统计
        mom_matches = sum(1 for d in corrected_data if d.get('mom_match', False))
        yoy_matches = sum(1 for d in corrected_data if d.get('yoy_match', False))
        
        # 有效的环比和同比数据点数量
        valid_mom = sum(1 for d in corrected_data if d.get('calculated_mom') is not None)
        valid_yoy = sum(1 for d in corrected_data if d.get('calculated_yoy') is not None)
        
        if valid_mom > 0:
            mom_accuracy = (mom_matches / valid_mom) * 100
            print(f"环比匹配率: {mom_matches}/{valid_mom} ({mom_accuracy:.1f}%)")
        
        if valid_yoy > 0:
            yoy_accuracy = (yoy_matches / valid_yoy) * 100
            print(f"同比匹配率: {yoy_matches}/{valid_yoy} ({yoy_accuracy:.1f}%)")
        
        # 误差统计
        mom_errors = [d['mom_error'] for d in corrected_data if d.get('mom_error') is not None]
        yoy_errors = [d['yoy_error'] for d in corrected_data if d.get('yoy_error') is not None]
        
        if mom_errors:
            avg_mom_error = sum(mom_errors) / len(mom_errors)
            max_mom_error = max(mom_errors)
            print(f"环比平均误差: {avg_mom_error:.3f}")
            print(f"环比最大误差: {max_mom_error:.3f}")
        
        if yoy_errors:
            avg_yoy_error = sum(yoy_errors) / len(yoy_errors)
            max_yoy_error = max(yoy_errors)
            print(f"同比平均误差: {avg_yoy_error:.3f}")
            print(f"同比最大误差: {max_yoy_error:.3f}")
    
    def print_comparison_results(self, city_name: str, city_data: List[Dict], 
                               processed_data: List[Dict], corrected_data: List[Dict], 
                               house_type: str = "新建商品住宅"):
        """
        打印矫正前后的对比结果
        
        Args:
            city_name: 城市名称
            city_data: 原始数据
            processed_data: 基础处理数据
            corrected_data: 矫正后数据
            house_type: 房屋类型
        """
        print("=" * 140)
        print(f"城市{house_type}销售价格指数数据处理结果 - {city_name} (矫正前后对比)")
        print("=" * 140)
        
        if not city_data:
            print(f"未找到城市 '{city_name}' 的数据")
            return
        
        print(f"\n数据时间范围: {city_data[0]['date']} 至 {city_data[-1]['date']}")
        print(f"数据记录数量: {len(city_data)} 条")
        
        # 显示原始数据
        print("\n" + "=" * 140)
        print("原始数据 (按时间排序)")
        print("=" * 140)
        print(f"{'日期':<12} {'环比':<10} {'同比':<10} {'数据文件'}")
        print("-" * 140)
        
        for data in city_data:
            filename = os.path.basename(data['filepath'])
            print(f"{data['date']:<12} {data['month_on_month']:<10.1f} {data['year_on_year']:<10.1f} {filename}")
        
        # 显示对比结果
        print("\n" + "=" * 140)
        print("矫正前后对比 (环比递推 vs 环比同比交叉验证)")
        print("=" * 140)
        print(f"{'日期':<10} {'原环比':<8} {'原同比':<8} {'基础值':<10} {'矫正值':<10} {'差异':<8} {'计算环比':<10} {'计算同比':<10} {'环比匹配':<8} {'同比匹配':<8}")
        print("-" * 140)
        
        for i, data in enumerate(corrected_data):
            basic_value = processed_data[i]['actual_value']
            corrected_value = data['actual_value']
            difference = corrected_value - basic_value
            
            # 获取通过矫正值计算出的环比和同比
            calc_mom = data.get('calculated_mom')
            calc_yoy = data.get('calculated_yoy')
            
            # 处理None值
            calc_mom_str = f"{calc_mom:.1f}" if calc_mom is not None else "-"
            calc_yoy_str = f"{calc_yoy:.1f}" if calc_yoy is not None else "-"
            
            mom_match = "✓" if data.get('mom_match', False) else "✗"
            yoy_match = "✓" if data.get('yoy_match', False) else "✗"
            
            print(f"{data['date']:<10} {data['month_on_month']:<8.1f} {data['year_on_year']:<8.1f} "
                  f"{basic_value:<10.2f} {corrected_value:<10.2f} {difference:<8.2f} "
                  f"{calc_mom_str:<10} {calc_yoy_str:<10} {mom_match:<8} {yoy_match:<8}")
        
        # 显示对比统计
        self._print_comparison_statistics(processed_data, corrected_data)
    
    def _print_comparison_statistics(self, processed_data: List[Dict], corrected_data: List[Dict]):
        """打印对比统计信息"""
        print("\n" + "=" * 140)
        print("对比统计信息")
        print("=" * 140)
        
        # 基础统计
        basic_final = processed_data[-1]['actual_value']
        corrected_final = corrected_data[-1]['actual_value']
        basic_max = max(d['actual_value'] for d in processed_data)
        corrected_max = max(d['actual_value'] for d in corrected_data)
        basic_min = min(d['actual_value'] for d in processed_data)
        corrected_min = min(d['actual_value'] for d in corrected_data)
        
        basic_growth = ((basic_final - 100) / 100) * 100
        corrected_growth = ((corrected_final - 100) / 100) * 100
        
        print(f"{'指标':<15} {'基础递推':<12} {'矫正后':<12} {'差异':<12}")
        print("-" * 60)
        print(f"{'最终值':<15} {basic_final:<12.2f} {corrected_final:<12.2f} {corrected_final-basic_final:<12.2f}")
        print(f"{'最高值':<15} {basic_max:<12.2f} {corrected_max:<12.2f} {corrected_max-basic_max:<12.2f}")
        print(f"{'最低值':<15} {basic_min:<12.2f} {corrected_min:<12.2f} {corrected_min-basic_min:<12.2f}")
        print(f"{'总体增长(%)':<15} {basic_growth:<12.2f} {corrected_growth:<12.2f} {corrected_growth-basic_growth:<12.2f}")
        
        # 矫正效果统计
        mom_matches = sum(1 for d in corrected_data if d.get('mom_match', False))
        yoy_matches = sum(1 for d in corrected_data if d.get('yoy_match', False))
        valid_mom = sum(1 for d in corrected_data if d.get('calculated_mom') is not None)
        valid_yoy = sum(1 for d in corrected_data if d.get('calculated_yoy') is not None)
        
        print(f"\n矫正效果:")
        if valid_mom > 0:
            mom_accuracy = (mom_matches / valid_mom) * 100
            print(f"环比匹配率: {mom_matches}/{valid_mom} ({mom_accuracy:.1f}%)")
        
        if valid_yoy > 0:
            yoy_accuracy = (yoy_matches / valid_yoy) * 100
            print(f"同比匹配率: {yoy_matches}/{valid_yoy} ({yoy_accuracy:.1f}%)")
        
        # 误差统计
        mom_errors = [d['mom_error'] for d in corrected_data if d.get('mom_error') is not None]
        yoy_errors = [d['yoy_error'] for d in corrected_data if d.get('yoy_error') is not None]
        
        if mom_errors:
            avg_mom_error = sum(mom_errors) / len(mom_errors)
            print(f"环比平均误差: {avg_mom_error:.3f}")
        
        if yoy_errors:
            avg_yoy_error = sum(yoy_errors) / len(yoy_errors)
            print(f"同比平均误差: {avg_yoy_error:.3f}")
    
    def print_classified_comparison_results(self, city_name: str, city_data: List[Dict], 
                                          processed_data: List[Dict], corrected_data: List[Dict], 
                                          house_type: str = "新建商品住宅", area_type: str = "90m2及以下"):
        """
        打印分类指数矫正前后的对比结果
        
        Args:
            city_name: 城市名称
            city_data: 原始数据
            processed_data: 基础处理数据
            corrected_data: 矫正后数据
            house_type: 房屋类型
            area_type: 面积类型
        """
        print("=" * 140)
        print(f"城市{house_type}销售价格分类指数数据处理结果 - {city_name} ({area_type}) (矫正前后对比)")
        print("=" * 140)
        
        if not city_data:
            print(f"未找到城市 '{city_name}' 的{house_type} {area_type} 数据")
            return
        
        print(f"\n数据时间范围: {city_data[0]['date']} 至 {city_data[-1]['date']}")
        print(f"数据记录数量: {len(city_data)} 条")
        print(f"房屋类型: {house_type}")
        print(f"面积类型: {area_type}")
        
        # 显示原始数据
        print("\n" + "=" * 140)
        print("原始数据 (按时间排序)")
        print("=" * 140)
        print(f"{'日期':<12} {'环比':<10} {'同比':<10} {'数据文件'}")
        print("-" * 140)
        
        for data in city_data:
            filename = os.path.basename(data['filepath'])
            print(f"{data['date']:<12} {data['month_on_month']:<10.1f} {data['year_on_year']:<10.1f} {filename}")
        
        # 显示对比结果
        print("\n" + "=" * 140)
        print("矫正前后对比 (环比递推 vs 环比同比交叉验证)")
        print("=" * 140)
        print(f"{'日期':<10} {'原环比':<8} {'原同比':<8} {'基础值':<10} {'矫正值':<10} {'差异':<8} {'计算环比':<10} {'计算同比':<10} {'环比匹配':<8} {'同比匹配':<8}")
        print("-" * 140)
        
        for i, data in enumerate(corrected_data):
            basic_value = processed_data[i]['actual_value']
            corrected_value = data['actual_value']
            difference = corrected_value - basic_value
            
            # 获取通过矫正值计算出的环比和同比
            calc_mom = data.get('calculated_mom')
            calc_yoy = data.get('calculated_yoy')
            
            # 处理None值
            calc_mom_str = f"{calc_mom:.1f}" if calc_mom is not None else "-"
            calc_yoy_str = f"{calc_yoy:.1f}" if calc_yoy is not None else "-"
            
            mom_match = "✓" if data.get('mom_match', False) else "✗"
            yoy_match = "✓" if data.get('yoy_match', False) else "✗"
            
            print(f"{data['date']:<10} {data['month_on_month']:<8.1f} {data['year_on_year']:<8.1f} "
                  f"{basic_value:<10.2f} {corrected_value:<10.2f} {difference:<8.2f} "
                  f"{calc_mom_str:<10} {calc_yoy_str:<10} {mom_match:<8} {yoy_match:<8}")
        
        # 显示对比统计
        self._print_comparison_statistics(processed_data, corrected_data)
    
    def process_city(self, city_name: str, house_type: str = "新建商品住宅", base_value: float = 100.0):
        """
        处理指定城市的数据并输出结果
        同时显示矫正前和矫正后的对比
        
        Args:
            city_name: 城市名称
            house_type: 房屋类型，"新建商品住宅" 或 "二手住宅"
            base_value: 基准值
        """
        # 提取城市数据
        city_data = self.extract_city_data(city_name, house_type)
        
        if not city_data:
            print(f"未找到城市 '{city_name}' 的{house_type}数据")
            return
        
        # 计算基础实际值
        processed_data = self.calculate_actual_values(city_data, base_value)
        
        # 计算矫正后的值
        corrected_data = self.calculate_corrected_values(city_data, base_value)
        
        # 打印对比结果
        self.print_comparison_results(city_name, city_data, processed_data, corrected_data, house_type)


def main():
    """主函数"""
    processor = CityPriceProcessor()
    
    print("城市房价指数数据处理工具 (矫正前后对比)")
    print("=" * 60)
    print("支持处理以下类型的房价指数：")
    print("1. 新建商品住宅销售价格指数")
    print("2. 二手住宅销售价格指数")
    print("3. 新建商品住宅销售价格分类指数")
    print("4. 二手住宅销售价格分类指数")
    print("=" * 60)
    
    while True:
        city_name = input("\n请输入城市名称 (输入 'quit' 退出): ").strip()
        
        if city_name.lower() == 'quit':
            print("程序退出")
            break
        
        if not city_name:
            print("请输入有效的城市名称")
            continue
        
        # 选择指数类型
        print("\n请选择指数类型：")
        print("1. 新建商品住宅销售价格指数 (默认)")
        print("2. 二手住宅销售价格指数")
        print("3. 新建商品住宅销售价格分类指数")
        print("4. 二手住宅销售价格分类指数")
        
        index_choice = input("请输入选择 (1-4，直接回车默认选择1): ").strip()
        
        if index_choice == '2':
            house_type = "二手住宅"
            is_classified = False
        elif index_choice == '3':
            house_type = "新建商品住宅"
            is_classified = True
        elif index_choice == '4':
            house_type = "二手住宅"
            is_classified = True
        else:
            house_type = "新建商品住宅"
            is_classified = False
        
        # 如果是分类指数，选择面积类型
        area_type = None
        if is_classified:
            print("\n请选择面积类型：")
            print("1. 90m2及以下 (默认)")
            print("2. 90-144m2")
            print("3. 144m2以上")
            
            area_choice = input("请输入选择 (1-3，直接回车默认选择1): ").strip()
            
            if area_choice == '2':
                area_type = "90-144m2"
            elif area_choice == '3':
                area_type = "144m2以上"
            else:
                area_type = "90m2及以下"
        
        # 处理数据
        if is_classified:
            print(f"\n正在处理 {city_name} 的{house_type}销售价格分类指数数据 ({area_type})...")
            try:
                processor.process_city_classified(city_name, house_type, area_type)
            except Exception as e:
                print(f"处理数据时发生错误: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"\n正在处理 {city_name} 的{house_type}销售价格指数数据...")
            try:
                processor.process_city(city_name, house_type)
            except Exception as e:
                print(f"处理数据时发生错误: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 140)


if __name__ == "__main__":
    main()
