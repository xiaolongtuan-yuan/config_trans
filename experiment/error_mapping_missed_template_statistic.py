# -*- coding: utf-8 -*-
"""
@Time ： 2025/5/9 00:16
@Auth ： xiaolongtuan
@File ：error_mapping_missed_template_statistic.py
"""
import os
import json
from collections import Counter


def analyze_missed_templates(input_dir, output_file):
    # 初始化计数器
    template_counter = Counter()

    # 遍历目录下所有_evaluate.json文件
    for filename in os.listdir(input_dir):
        if filename.endswith('_evaluate.json'):
            file_path = os.path.join(input_dir, filename)

            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # 统计missed_templates
                if 'missed_templates' in data:
                    template_counter.update(data['missed_templates'])
    # 将结果按照使用量降序排列
    sorted_templates = sorted(template_counter.items(), key=lambda x: x[1], reverse=True)
    # 将结果保存到指定文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_templates, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    name = 'multi_module'
    vendors = ['HUAWEI', 'Juniper', 'Cisco']
    grammatical_accuracy = {}
    for vendor1 in vendors:
        for vendor2 in vendors:
            if vendor1 == vendor2:
                continue
            input_directory = f'./exper_data/translated_config_with_{name}/400/{vendor1}/{vendor2}/'
            output_file = f'./exper_res/missed_templates_frequency/{vendor1}_{vendor2}_missed_templates_frequency.json'
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            analyze_missed_templates(input_directory, output_file)
            print(f"分析完成，结果已保存到 {output_file}")