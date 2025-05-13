# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：exper_data_translated.py
"""
import re
from collections import Counter, defaultdict
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
    name = 'full_process'
    num = 300
    vendors = ['HUAWEI', 'Juniper', 'Cisco']
    grammatical_accuracy = {}
    for vendor1 in vendors:
        for vendor2 in vendors:
            if vendor1 == vendor2:
                continue
            error_statistic = defaultdict(int)
            error_mapping_statistic = defaultdict(int)
            missing_template = {}
            grammatical_accuracy[f'{vendor1}_{vendor2}'] = []
            folder_path = f'./exper_data/translated_config_with_{name}/{num}/{vendor1}/{vendor2}/'
            # folder_path = f'./exper_data/translated_config_with_use_freq/400/{vendor1}/{vendor2}/'
            map_rule_extension = '_map_rules.json'
            label_template_extension = '_expected_temp.json'
            result_extension = '_evaluate.json'
            # 获取所有匹配的文件
            match_rule_files = find_files(folder_path.format(vendors[0], vendors[1]), map_rule_extension)
            label_template_files = find_files(folder_path.format(vendors[0], vendors[1]), label_template_extension)
            result_files = find_files(folder_path.format(vendors[0], vendors[1]), result_extension)
            for i in range(len(match_rule_files)):
                matched_file = match_rule_files[i]
                label_template_file = matched_file.replace(map_rule_extension, label_template_extension)
                result_file = matched_file.replace(map_rule_extension, result_extension)

                # label_template_file = label_template_files[i]
                # result_file = result_files[i]
                # 读取匹配规则文件
                match_rule_data = load_json_file(matched_file)
                # 读取标签模板文件
                label_template_data = list(load_json_file(label_template_file))
                # 读取结果文件
                result_data = load_json_file(result_file)
                grammatical_accuracy[f'{vendor1}_{vendor2}'].append(result_data["grammatical_accuracy"])
                # template_count_result = Counter(label_template_data)
                # 统计错误模板数量
                for map_rule_str, count in match_rule_data.items():
                    map_rule = ast.literal_eval(map_rule_str)
                    # print(f"map_rule_str: {map_rule_str}")
                    flag = False
                    for item in map_rule[1]:
                        if vendor2 == 'Juniper':
                            trans_template = ''
                            if item['parent_command'] != []:
                                trans_template = ' '.join(item['parent_command'])
                            trans_template = trans_template + ' ' + item['trans_command'] if trans_template != '' else item['trans_command']
                        else:
                            trans_template = item['trans_command']

                        has_mappping = False
                        for label_template in label_template_data:
                            label_template_re = re.sub(r"\[[^\]]+\]", r'(\\S+)', label_template)
                            if re.match(label_template_re, trans_template):
                                has_mappping = True
                                break
                        if has_mappping: # 计算是否匹配
                            error_statistic[map_rule[0]] += count
                            flag = True
                    if flag: # 映射是有用的
                        error_mapping_statistic[map_rule[0]] += 1
                    else:
                        error_mapping_statistic[map_rule[0]] += 0


                missing_template_count_result = Counter(result_data["missed_templates"])
                # 统计缺失模板数量
                for template in missing_template_count_result:
                    if template not in missing_template.keys():
                        missing_template[template] = missing_template_count_result[template]
                    else:
                        missing_template[template] += missing_template_count_result[template]
            # 保存数据
            error_statistic = sorted(error_statistic.items(), key=lambda x: x[1], reverse=True)
            os.makedirs('./exper_res/scale_177_error_mapping_rules_freq', exist_ok=True)
            error_statistic_path = f'./exper_res/scale_177_error_mapping_rules_freq/{vendor1}_{vendor2}_error_mapping_rules_freq.json'
            with open(error_statistic_path, mode='w', encoding='utf-8') as f:
                json.dump(error_statistic, f, ensure_ascii=False, indent=2)
            error_mapping_rules = [rule for rule, used in error_mapping_statistic.items() if used == 0]
            with open(f'../dataset_multi_vendor_config/mapping_template_library/error_mapping/{vendor1}_{vendor2}.json', mode='w', encoding='utf-8') as f:
                json.dump(error_mapping_rules, f, ensure_ascii=False, indent=2)
            print(f"Error mapping rules frequency saved to {error_statistic_path}")
            missing_template = sorted(missing_template.items(), key=lambda x: x[1], reverse=True)
            missing_template_path = f'./exper_res/scale_177_error_mapping_rules_freq/{vendor1}_{vendor2}_missing_template_statistic.json'
            with open(missing_template_path, mode='w', encoding='utf-8') as f:
                json.dump(missing_template, f, ensure_ascii=False, indent=2)
            print(f"Missing template frequency saved to {missing_template_path}")

    for key, value in grammatical_accuracy.items():
        print('task:', key, 'grammatical_accuracy_result:', np.mean(value))
    all_values = [np.mean(v) for v in grammatical_accuracy.values()]
    print('Overall grammatical_accuracy average:', np.mean(all_values))

if __name__ == "__main__":
    main()
