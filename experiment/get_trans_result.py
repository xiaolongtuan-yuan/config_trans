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
    num = "valid_data_100_from_all_tau_0_5"
    # num = "500"
    # scale = '500'

    vendors = ['HUAWEI', 'Juniper', 'Cisco']
    grammatical_accuracy = defaultdict(list)
    command_accuracy = defaultdict(list)

    llm_command_ratio = defaultdict(list)
    heuristic_command_ratio = defaultdict(list)
    command_for_llm_rate = defaultdict(list)
    command_for_heuristic_rate = defaultdict(list)

    for vendor1 in vendors:
        for vendor2 in vendors:
            if vendor1 == vendor2:
                continue
            folder_path = f'./exper_data/translated_config_with_{name}/{num}/{vendor1}/{vendor2}/'
            result_extension = '_evaluate.json'
            # 获取所有匹配的文件
            match_rule_files = find_files(folder_path.format(vendors[0], vendors[1]), result_extension)
            for i in range(len(match_rule_files)):
                result_file = match_rule_files[i]
                result_data = load_json_file(result_file)
                grammatical_accuracy[f'{vendor1}_{vendor2}'].append(result_data["grammatical_accuracy"])
                command_accuracy[f'{vendor1}_{vendor2}'].append(result_data["command_accuracy"])
                llm_command_ratio[f'{vendor1}_{vendor2}'].append(result_data["llm_command_ratio"])
                heuristic_command_ratio[f'{vendor1}_{vendor2}'].append(result_data["heuristic_command_ratio"])
                command_for_llm_rate[f'{vendor1}_{vendor2}'].append(result_data["command_for_llm_rate"])
                command_for_heuristic_rate[f'{vendor1}_{vendor2}'].append(result_data["command_for_heuristic_rate"])

    for key, value in grammatical_accuracy.items():
        print('task:', key, 'grammatical_accuracy_result:', np.mean(value))
    all_values = [np.mean(v) for v in grammatical_accuracy.values()]
    print('Overall grammatical_accuracy average:', np.mean(all_values))

    for key, value in command_accuracy.items():
        print('task:', key, 'command_accuracy_result:', np.mean(value))
    all_values = [np.mean(v) for v in command_accuracy.values()]
    print('Overall command_accuracy average:', np.mean(all_values))

    for key, value in llm_command_ratio.items():
        print('task:', key, 'llm_command_ratio_result:', np.mean(value))
    all_values = [np.mean(v) for v in llm_command_ratio.values()]
    print('Overall llm_command_ratio average:', np.mean(all_values))

    for key, value in command_for_llm_rate.items():
        print('task:', key, 'command_for_llm_rate_result:', np.mean(value))
    all_values = [np.mean(v) for v in command_for_llm_rate.values()]
    print('Overall command_for_llm_rate average:', np.mean(all_values))

    for key, value in heuristic_command_ratio.items():
        print('task:', key, 'heuristic_command_ratio_result:', np.mean(value))
    all_values = [np.mean(v) for v in heuristic_command_ratio.values()]
    print('Overall heuristic_command_ratio average:', np.mean(all_values))

    for key, value in command_for_heuristic_rate.items():
        print('task:', key, 'command_for_heuristic_rate_result:', np.mean(value))
    all_values = [np.mean(v) for v in command_for_heuristic_rate.values()]
    print('Overall command_for_heuristic_rate average:', np.mean(all_values))




if __name__ == "__main__":
    main()
