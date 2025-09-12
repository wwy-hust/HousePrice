#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理所有城市的房价指数数据
生成8种类型的JSON文件：
1. 新建商品住宅销售价格指数
2. 二手住宅销售价格指数
3. 新建商品住宅销售价格分类指数 - 90m2及以下
4. 新建商品住宅销售价格分类指数 - 90-144m2
5. 新建商品住宅销售价格分类指数 - 144m2以上
6. 二手住宅销售价格分类指数 - 90m2及以下
7. 二手住宅销售价格分类指数 - 90-144m2
8. 二手住宅销售价格分类指数 - 144m2以上
"""

import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict
from city_price_processor import CityPriceProcessor, PriceIndexCalculationEngine


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, output_dir: str = "results"):
        """
        初始化批量处理器
        
        Args:
            output_dir: 输出目录
        """
        self.processor = CityPriceProcessor()
        self.engine = PriceIndexCalculationEngine()
        self.output_dir = output_dir
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 定义处理配置
        self.index_configs = [
            {
                "name": "新建商品住宅销售价格指数",
                "filename": "new_house_basic_index.json",
                "house_type": "新建商品住宅",
                "is_classified": False,
                "area_type": None
            },
            {
                "name": "二手住宅销售价格指数", 
                "filename": "used_house_basic_index.json",
                "house_type": "二手住宅",
                "is_classified": False,
                "area_type": None
            },
            {
                "name": "新建商品住宅销售价格分类指数 - 90m2及以下",
                "filename": "new_house_classified_90_below.json",
                "house_type": "新建商品住宅",
                "is_classified": True,
                "area_type": "90m2及以下"
            },
            {
                "name": "新建商品住宅销售价格分类指数 - 90-144m2",
                "filename": "new_house_classified_90_144.json",
                "house_type": "新建商品住宅",
                "is_classified": True,
                "area_type": "90-144m2"
            },
            {
                "name": "新建商品住宅销售价格分类指数 - 144m2以上",
                "filename": "new_house_classified_144_above.json",
                "house_type": "新建商品住宅",
                "is_classified": True,
                "area_type": "144m2以上"
            },
            {
                "name": "二手住宅销售价格分类指数 - 90m2及以下",
                "filename": "used_house_classified_90_below.json",
                "house_type": "二手住宅",
                "is_classified": True,
                "area_type": "90m2及以下"
            },
            {
                "name": "二手住宅销售价格分类指数 - 90-144m2",
                "filename": "used_house_classified_90_144.json",
                "house_type": "二手住宅",
                "is_classified": True,
                "area_type": "90-144m2"
            },
            {
                "name": "二手住宅销售价格分类指数 - 144m2以上",
                "filename": "used_house_classified_144_above.json",
                "house_type": "二手住宅",
                "is_classified": True,
                "area_type": "144m2以上"
            }
        ]
    
    def get_all_cities(self) -> List[str]:
        """
        获取所有城市列表
        
        Returns:
            城市名称列表
        """
        cities = set()
        
        if self.processor.data_files:
            # 从最新的文件中获取城市列表
            latest_file = self.processor.data_files[-1]
            try:
                tree = ET.parse(latest_file)
                root = tree.getroot()
                
                for table in root.findall('.//table'):
                    data_rows = table.find('.//data')
                    if data_rows is not None:
                        for row in data_rows.findall('row'):
                            cells = row.findall('cell')
                            if len(cells) > 0 and cells[0].text:
                                city = cells[0].text.strip()
                                if city and city != '城市':
                                    cities.add(city)
            except Exception as e:
                print(f"解析城市列表时出错: {e}")
        
        return sorted(list(cities))
    
    def process_city_index(self, city: str, config: Dict) -> Dict:
        """
        处理单个城市的指定指数类型
        
        Args:
            city: 城市名称
            config: 指数配置
            
        Returns:
            处理结果字典
        """
        try:
            # 提取数据
            if config["is_classified"]:
                city_data = self.processor.extract_city_classified_data(
                    city, config["house_type"], config["area_type"]
                )
            else:
                city_data = self.processor.extract_city_data(
                    city, config["house_type"]
                )
            
            if not city_data:
                return {
                    "city": city,
                    "index_type": config["name"],
                    "status": "no_data",
                    "data_count": 0,
                    "time_range": None,
                    "basic_result": None,
                    "corrected_result": None,
                    "statistics": None
                }
            
            # 使用通用引擎计算
            basic_result = self.engine.calculate_actual_values(city_data)
            corrected_result = self.engine.calculate_corrected_values(city_data)
            
            # 计算统计信息
            statistics = self._calculate_statistics(corrected_result)
            
            return {
                "city": city,
                "index_type": config["name"],
                "house_type": config["house_type"],
                "area_type": config.get("area_type"),
                "status": "success",
                "data_count": len(city_data),
                "time_range": {
                    "start": city_data[0]["date"],
                    "end": city_data[-1]["date"]
                },
                "raw_data": city_data,
                "basic_result": basic_result,
                "corrected_result": corrected_result,
                "statistics": statistics
            }
            
        except Exception as e:
            return {
                "city": city,
                "index_type": config["name"],
                "status": "error",
                "error_message": str(e),
                "data_count": 0,
                "time_range": None,
                "basic_result": None,
                "corrected_result": None,
                "statistics": None
            }
    
    def _calculate_statistics(self, corrected_result: List[Dict]) -> Dict:
        """
        计算统计信息
        
        Args:
            corrected_result: 矫正后的结果
            
        Returns:
            统计信息字典
        """
        if not corrected_result:
            return None
        
        # 基本统计
        actual_values = [d['actual_value'] for d in corrected_result]
        final_value = corrected_result[-1]['actual_value']
        max_value = max(actual_values)
        min_value = min(actual_values)
        total_growth = ((final_value - 100) / 100) * 100
        
        # 验证统计
        mom_matches = sum(1 for d in corrected_result if d.get('mom_match', False))
        yoy_matches = sum(1 for d in corrected_result if d.get('yoy_match', False))
        valid_mom = sum(1 for d in corrected_result if d.get('calculated_mom') is not None)
        valid_yoy = sum(1 for d in corrected_result if d.get('calculated_yoy') is not None)
        
        # 误差统计
        mom_errors = [d['mom_error'] for d in corrected_result if d.get('mom_error') is not None]
        yoy_errors = [d['yoy_error'] for d in corrected_result if d.get('yoy_error') is not None]
        
        return {
            "final_value": final_value,
            "max_value": max_value,
            "min_value": min_value,
            "total_growth_percent": total_growth,
            "mom_match_rate": (mom_matches / valid_mom * 100) if valid_mom > 0 else 0,
            "yoy_match_rate": (yoy_matches / valid_yoy * 100) if valid_yoy > 0 else 0,
            "mom_matches": f"{mom_matches}/{valid_mom}",
            "yoy_matches": f"{yoy_matches}/{valid_yoy}",
            "avg_mom_error": sum(mom_errors) / len(mom_errors) if mom_errors else 0,
            "avg_yoy_error": sum(yoy_errors) / len(yoy_errors) if yoy_errors else 0
        }
    
    def process_all(self):
        """处理所有城市的所有指数类型"""
        print("=" * 80)
        print("批量处理所有城市房价指数数据")
        print("=" * 80)
        
        # 获取所有城市
        cities = self.get_all_cities()
        print(f"发现 {len(cities)} 个城市")
        
        # 处理每种指数类型
        for config in self.index_configs:
            print(f"\n正在处理: {config['name']}")
            print("-" * 60)
            
            results = []
            success_count = 0
            no_data_count = 0
            error_count = 0
            
            for i, city in enumerate(cities, 1):
                print(f"[{i:2d}/{len(cities)}] 处理 {city}...", end=" ")
                
                result = self.process_city_index(city, config)
                results.append(result)
                
                if result["status"] == "success":
                    success_count += 1
                    final_value = result["statistics"]["final_value"]
                    growth = result["statistics"]["total_growth_percent"]
                    print(f"✓ (最终值: {final_value:.2f}, 变化: {growth:+.2f}%)")
                elif result["status"] == "no_data":
                    no_data_count += 1
                    print("⚠ (无数据)")
                else:
                    error_count += 1
                    print(f"✗ (错误: {result.get('error_message', '未知错误')})")
            
            # 保存结果
            output_file = os.path.join(self.output_dir, config["filename"])
            
            # 创建输出数据
            output_data = {
                "index_type": config["name"],
                "house_type": config["house_type"],
                "area_type": config.get("area_type"),
                "generated_at": datetime.now().isoformat(),
                "total_cities": len(cities),
                "success_count": success_count,
                "no_data_count": no_data_count,
                "error_count": error_count,
                "cities": results
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n结果已保存到: {output_file}")
            print(f"统计: 成功 {success_count}, 无数据 {no_data_count}, 错误 {error_count}")
        
        print("\n" + "=" * 80)
        print("🎉 批量处理完成！")
        print("=" * 80)
        
        # 生成汇总报告
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """生成汇总报告"""
        print("\n生成汇总报告...")
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_index_types": len(self.index_configs),
            "output_directory": self.output_dir,
            "files": []
        }
        
        for config in self.index_configs:
            filename = config["filename"]
            filepath = os.path.join(self.output_dir, filename)
            
            file_info = {
                "filename": filename,
                "index_type": config["name"],
                "house_type": config["house_type"],
                "area_type": config.get("area_type"),
                "file_exists": os.path.exists(filepath)
            }
            
            if file_info["file_exists"]:
                file_info["file_size"] = os.path.getsize(filepath)
            
            summary["files"].append(file_info)
        
        # 保存汇总报告
        summary_file = os.path.join(self.output_dir, "summary_report.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"汇总报告已保存到: {summary_file}")
        
        # 打印文件列表
        print(f"\n生成的文件列表:")
        for file_info in summary["files"]:
            status = "✓" if file_info["file_exists"] else "✗"
            size = f" ({file_info.get('file_size', 0)} bytes)" if file_info["file_exists"] else ""
            print(f"  {status} {file_info['filename']}{size}")


def main():
    """主函数"""
    print("城市房价指数批量处理工具")
    print("将处理所有70个城市的8种房价指数类型")
    
    # 询问用户是否确认
    response = input("\n是否开始批量处理？这可能需要几分钟时间 (y/N): ").strip().lower()
    
    if response != 'y':
        print("取消处理")
        return
    
    try:
        # 创建批量处理器并开始处理
        processor = BatchProcessor()
        processor.process_all()
        
        print(f"\n✅ 所有处理完成！结果文件保存在 '{processor.output_dir}' 目录中。")
        
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
