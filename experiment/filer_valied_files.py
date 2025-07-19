# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：error_mapping_rule_statistic_multi_module.py
统计翻译过程中使用的映射规则错误率以及在标签中未被翻译到的命令模版频率
"""
import re
from collections import Counter, defaultdict
import os
import json
import ast
import numpy as np


def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_files(directory, extension):
    """查找指定目录下的所有文件"""
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(extension)]


def main():
    name = 'all_data_2800'
    num = "valid_data_all_from_all"
    scale = '2800'
    valid_data_path = '../syntactic_check/candidate_file_names/final_useful_file_name.json'

    vendors = ['HUAWEI', 'Juniper', 'Cisco']
    grammatical_accuracy = {}
    command_accuracy = {}
    llm_command_ratio = {}
    useful_file_name = defaultdict(set)
    for vendor1 in vendors:
        for vendor2 in vendors:
            if vendor1 == vendor2:
                continue
            grammatical_accuracy[f'{vendor1}_{vendor2}'] = []
            command_accuracy[f'{vendor1}_{vendor2}'] = []
            llm_command_ratio[f'{vendor1}_{vendor2}'] = []
            folder_path = f'./exper_data/translated_config_with_{name}/{num}/{vendor1}/{vendor2}/'
            map_rule_extension = '_map_rules.json'
            label_template_extension = '_expected_temp.json'
            result_extension = '_evaluate.json'
            # 获取所有匹配的文件
            valid_files = load_json_file(valid_data_path)
            for file_name in valid_files[:100]:
                result_file = folder_path + file_name + result_extension
                result_data = load_json_file(result_file)
                grammatical_accuracy[f'{vendor1}_{vendor2}'].append(result_data["grammatical_accuracy"])
                command_accuracy[f'{vendor1}_{vendor2}'].append(result_data["command_accuracy"])
                llm_command_ratio[f'{vendor1}_{vendor2}'].append(result_data["llm_command_ratio"])

    for key, value in grammatical_accuracy.items():
        print('task:', key, 'grammatical_accuracy_result:', np.mean(value))
    # 计算所有任务的平均值
    all_values = [np.mean(v) for v in grammatical_accuracy.values()]
    print('Overall grammatical_accuracy average:', np.mean(all_values))
    for key, value in command_accuracy.items():
        print('task:', key, 'command_accuracy_result:', np.mean(value))
    # 计算所有任务的平均值
    all_values = [np.mean(v) for v in command_accuracy.values()]
    print('Overall command_accuracy average:', np.mean(all_values))
    for key, value in llm_command_ratio.items():
        print('task:', key, 'llm_command_ratio_result:', np.mean(value))
    # 计算所有任务的平均值
    all_values = [np.mean(v) for v in llm_command_ratio.values()]
    print('Overall llm_command_ratio average:', np.mean(all_values))


if __name__ == "__main__":
    main()
