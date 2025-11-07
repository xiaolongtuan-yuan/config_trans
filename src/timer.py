# -*- coding: utf-8 -*-
"""
@Time ： 2025/1/15
@Auth ： AI Assistant
@File ：timer.py
@Description ：翻译过程计时器，用于统计各个阶段的耗时
"""
import time
from typing import Dict, List, Optional
import json


class TranslationTimer:
    """翻译过程计时器"""
    
    def __init__(self):
        self.start_time = None
        self.stage_times = {}
        self.current_stage = None
        self.stage_start_time = None
        self.total_time = 0.0
        
    def start_total_timer(self):
        """开始总计时"""
        self.start_time = time.time()
        
    def start_stage_timer(self, stage_name: str):
        """开始某个阶段的计时"""
        # 如果之前有阶段在计时，先结束它
        if self.current_stage and self.stage_start_time:
            self.end_stage_timer()
            
        self.current_stage = stage_name
        self.stage_start_time = time.time()
        
    def end_stage_timer(self):
        """结束当前阶段的计时"""
        if self.current_stage and self.stage_start_time:
            stage_duration = time.time() - self.stage_start_time
            self.stage_times[self.current_stage] = stage_duration
            self.current_stage = None
            self.stage_start_time = None
            
    def end_total_timer(self):
        """结束总计时"""
        if self.start_time:
            self.total_time = time.time() - self.start_time
            # 确保最后一个阶段也被记录
            if self.current_stage and self.stage_start_time:
                self.end_stage_timer()
                
    def get_stage_time(self, stage_name: str) -> float:
        """获取指定阶段的耗时"""
        return self.stage_times.get(stage_name, 0.0)
        
    def get_total_time(self) -> float:
        """获取总耗时"""
        return self.total_time
        
    def get_all_times(self) -> Dict[str, float]:
        """获取所有阶段的耗时"""
        times = self.stage_times.copy()
        times['total'] = self.total_time
        return times
        
    def reset(self):
        """重置计时器"""
        self.start_time = None
        self.stage_times = {}
        self.current_stage = None
        self.stage_start_time = None
        self.total_time = 0.0


class BatchTimer:
    """批量翻译计时器，用于统计多次翻译的平均耗时"""
    
    def __init__(self):
        self.timers: List[TranslationTimer] = []
        self.average_times = {}
        
    def add_timer(self, timer: TranslationTimer):
        """添加一个翻译计时器"""
        self.timers.append(timer)
        
    def calculate_averages(self) -> Dict[str, float]:
        """计算所有阶段的平均耗时"""
        if not self.timers:
            return {}
            
        # 获取所有阶段名称
        all_stages = set()
        for timer in self.timers:
            all_stages.update(timer.stage_times.keys())
        all_stages.add('total')
        
        # 计算每个阶段的平均耗时
        for stage in all_stages:
            times = []
            for timer in self.timers:
                if stage == 'total':
                    times.append(timer.get_total_time())
                else:
                    times.append(timer.get_stage_time(stage))
            
            if times:
                self.average_times[stage] = sum(times) / len(times)
                
        return self.average_times
        
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """获取统计信息"""
        averages = self.calculate_averages()
        
        # 计算每个阶段的最小值、最大值、标准差
        statistics = {}
        all_stages = set()
        for timer in self.timers:
            all_stages.update(timer.stage_times.keys())
        all_stages.add('total')
        
        for stage in all_stages:
            times = []
            for timer in self.timers:
                if stage == 'total':
                    times.append(timer.get_total_time())
                else:
                    times.append(timer.get_stage_time(stage))
            
            if times:
                statistics[stage] = {
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'count': len(times)
                }
                
                # 计算标准差
                if len(times) > 1:
                    mean = statistics[stage]['average']
                    variance = sum((x - mean) ** 2 for x in times) / (len(times) - 1)
                    statistics[stage]['std'] = variance ** 0.5
                else:
                    statistics[stage]['std'] = 0.0
                    
        return statistics
        
    def save_statistics(self, file_path: str):
        """保存统计信息到文件"""
        stats = self.get_statistics()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
            
    def print_statistics(self):
        """打印统计信息"""
        stats = self.get_statistics()
        print("\n=== 翻译耗时统计 ===")
        print(f"总翻译次数: {len(self.timers)}")
        print(f"{'阶段':<20} {'平均耗时(s)':<12} {'最小耗时(s)':<12} {'最大耗时(s)':<12} {'标准差(s)':<12}")
        print("-" * 80)
        
        for stage, data in stats.items():
            print(f"{stage:<20} {data['average']:<12.4f} {data['min']:<12.4f} {data['max']:<12.4f} {data['std']:<12.4f}")
            
        print("\n=== 各阶段耗时占比 ===")
        total_avg = stats.get('total', {}).get('average', 0)
        if total_avg > 0:
            for stage, data in stats.items():
                if stage != 'total':
                    percentage = (data['average'] / total_avg) * 100
                    print(f"{stage:<20} {percentage:>8.2f}%")
