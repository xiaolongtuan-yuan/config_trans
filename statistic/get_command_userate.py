# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/14 13:16
@Auth ： xiaolongtuan
@File ：get_command_userate.py
"""
import json
import os
from collections import Counter, defaultdict

data_scale_dirs = [
    'test_data_400',
    'test_data_1200',
    'test_data_2000',
    'test_data_2800'
]

def count_command_freq(command_data, parent_template, command_freq):
    if isinstance(command_data, dict):
        # 处理当前节点
        if 'template' in command_data:
            template = command_data['template']
            sub_command_freq[parent_template][template] += 1

        # 递归处理子节点
        for key, value in command_data.items():
            if isinstance(value, dict):
                count_command_freq(value, parent_template, command_freq)
            elif isinstance(value, list):
                for item in value:
                    count_command_freq(item, parent_template, command_freq)


for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
    # 初始化统计字典
    root_command_freq = defaultdict(int)
    sub_command_freq = defaultdict(lambda: defaultdict(int))

    for data_scale_dir in data_scale_dirs:
        if vendor == 'Juniper':
            train_data_path = '../experiment/test_dataset/' + data_scale_dir + '/command_tree/Juniper_subdivided'
        else:
            train_data_path = '../experiment/test_dataset/' + data_scale_dir + '/command_tree/' + vendor

        # 遍历所有json文件
        for file in os.listdir(train_data_path):
            if file.endswith('.json'):
                with open(os.path.join(train_data_path, file), 'r') as f:
                    data = json.load(f)

                for root_command, detail in data.items():
                    root_command_template = detail['template']
                    root_command_freq[root_command_template] += 1
                    sub_command_freq[root_command_template][root_command_template] += 1

                    count_command_freq(detail, root_command_template, sub_command_freq)

    # 保存统计结果
    output_dir = f'../experiment/test_dataset/template_used'
    os.makedirs(output_dir, exist_ok=True)

    # 保存根命令频率
    with open(f'{output_dir}/{vendor}_root_command_frequency.json', 'w') as f:
        json.dump(root_command_freq, f, indent=4)

    # 保存子命令频率
    with open(f'{output_dir}/{vendor}_sub_template_frequency.json', 'w') as f:
        json.dump(sub_command_freq, f, indent=4)
