# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：exper_data_translated.py
"""
import sys
sys.path.append("/data/public/hrx/Repositories/config_trans")
from collections import Counter
import os
import json
from tqdm import tqdm  # 用于显示进度条
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
    vendors = ['HUAWEI', 'Juniper', 'Cisco']
    grammatical_accuracy = {}
    for vendor1 in vendors:
        for vendor2 in vendors:
            if vendor1 == vendor2:
                continue
            error_statistic = {}
            grammatical_accuracy[f'{vendor1}_{vendor2}'] = []
            folder_path = f'./experiment/exper_data/translated_config_with_scale400/400/{vendor1}/{vendor2}/' 
            map_rule_extension = '_map_rules.json'
            label_template_extension = '_temp.json'
            result_extension = '_evaluate.json'
            # 获取所有匹配的文件
            match_rule_files = find_files(folder_path.format(vendors[0], vendors[1]), map_rule_extension)
            label_template_files = find_files(folder_path.format(vendors[0], vendors[1]), label_template_extension)
            result_files = find_files(folder_path.format(vendors[0], vendors[1]), result_extension)
            for i in range(len(match_rule_files)):
                matched_file = match_rule_files[i]
                label_template_file = label_template_files[i]
                result_file = result_files[i]
                # 读取匹配规则文件
                match_rule_data = load_json_file(matched_file)
                # 读取标签模板文件
                label_template_data = list(load_json_file(label_template_file))
                # 读取结果文件
                result_data = load_json_file(result_file)
                grammatical_accuracy[f'{vendor1}_{vendor2}'].append(result_data["grammatical_accuracy"])
                # 使用Counter统计出现次数
                template_count_result = Counter(label_template_data)
                for map_rule_str, count in match_rule_data.items():
                    map_rule = ast.literal_eval(map_rule_str)
                    # print(f"map_rule_str: {map_rule_str}")
                    for item in map_rule[1]:
                        if vendor2 == 'Juniper':
                            trans_template = ''
                            if item['parent_command'] != []:
                                for parent_tempalte in item['parent_command']:
                                    trans_template = trans_template + ' ' + parent_tempalte
                            trans_template = trans_template + ' ' + item['trans_command']
                        else:
                            trans_template = item['trans_command']
                        if trans_template not in template_count_result.keys():
                            # 统计错误类型
                            if map_rule[0] not in error_statistic.keys():
                                error_statistic[map_rule[0]] = count
                            else:
                                error_statistic[map_rule[0]] += count
            error_statistic = sorted(error_statistic.items(), key=lambda x: x[1], reverse=True)
            error_statistic_path = f'./experiment/exper_res/scale_400_error_mapping_rules_freq/{vendor1}_{vendor2}_error_mapping_rules_freq.json'
            with open(error_statistic_path, mode='w', encoding='utf-8') as f:
                json.dump(error_statistic, f, ensure_ascii=False, indent=2)
            print(f"Error mapping rules frequency saved to {error_statistic_path}")
    
    for key, value in grammatical_accuracy.items():
        print('task:', key, 'grammatical_accuracy_result:', np.mean(value))

if __name__ == "__main__":
    main()
