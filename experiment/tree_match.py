# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:28
@Auth ： xiaolongtuan
@File ：tree_match.py
"""
import os
import json
import re

def load_config_model(config_model_path):
    """加载配置模板"""
    with open(config_model_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_template(command, config_model):
    """递归查找命令对应的模板"""
    for template, details in config_model.items():
        # 使用正则表达式匹配模板
        # pattern = template.replace('[', r'\[').replace(']', r'\]')
        pattern = re.sub(r'\[parameter\d+\]', r'[\\w\\s]+', template)
        if re.match(pattern, command):
            return template
        # 递归查找子命令
        if isinstance(details, dict) and 'template' not in details:
            sub_template = find_template(command, details)
            if sub_template:
                return sub_template
    return None

def parse_config_file(file_path, config_model):
    """解析配置文件为模板序列"""
    templates = []
    extra_commands = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 去除前后空格和缩进
            command = line.strip()
            if command:
                template = find_template(command, config_model)
                if template:
                    templates.append(template if template else command)
                else:
                    extra_commands.append(command)
    return templates, extra_commands

def calculate_match_ratio(result_templates, expected_templates, result_extra_commands, expected_extra_commands):
    """计算翻译的模板序列的匹配度"""
    match_count = 0
    for result_template in result_templates:
        if result_template in expected_templates:
            match_count += 1
            expected_templates.remove(result_template)
    for result_extra_command in result_extra_commands:
        if result_extra_command in expected_extra_commands:
            match_count += 1
            expected_extra_commands.remove(result_extra_command)


    return match_count / (len(result_templates) + len(result_extra_commands))



target_vendor = 'HUAWEI'
cisco_huawei_config_dir = './exper_data/cisco_translated_config/HUAWEI'
cisco_to_huawei_config_files = [f for f in os.listdir(cisco_huawei_config_dir) if f.endswith('.txt')]
huawei_real_config_dir = './exper_data/HUAWEI'

config_model = f'../dataset_multi_vendor_config/config_model/{target_vendor}.json'
config_model = load_config_model(config_model)

total_match_ratio = 0
file_count = len(cisco_to_huawei_config_files)

for file_name in cisco_to_huawei_config_files:
    file_result = os.path.join(cisco_huawei_config_dir, file_name)
    file_expected = os.path.join(huawei_real_config_dir, file_name)

    # 解析配置文件
    result_templates, result_extra_command = parse_config_file(file_result, config_model)
    expected_templates, expected_extra_command = parse_config_file(file_expected, config_model)

    # 计算匹配度
    match_ratio = calculate_match_ratio(result_templates, expected_templates, result_extra_command, expected_extra_command)
    total_match_ratio += match_ratio

# 计算并输出平均匹配度
average_match_ratio = total_match_ratio / file_count if file_count > 0 else 0
print(f"\nAverage Match Ratio: {average_match_ratio:.2f}")


# Average Exact Match Ratio: 0.70
# Average Tree Match Ratio: 0.91
