# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/14 13:16
@Auth ： xiaolongtuan
@File ：get_command_userate.py
"""
import json
from collections import Counter

# 读取原始数据
for vendor in ['Cisco', 'Huawei', 'Juniper']:
    with open(f'statistic_res/{vendor}_template_used_statistic.json', 'r') as f:
        data = json.load(f)

    # 统计命令使用频率
    command_freq = Counter(data)

    # 按频率降序排序
    sorted_freq = dict(sorted(command_freq.items(), key=lambda item: item[1], reverse=True))

    # 保存为新的json文件
    with open(f'use_freq/{vendor}_template_frequency.json', 'w') as f:
        json.dump(sorted_freq, f, indent=4)
