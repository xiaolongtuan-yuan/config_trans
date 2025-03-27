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
        # 递归查找子命令
        if isinstance(details, dict) and 'template' in details:
            sub_template = find_template(command, details)
            if sub_template:
                return sub_template

        # 使用正则表达式匹配模板
        if template == 'template':
            pattern = re.sub(r'\[parameter\d+\]', r'(\\S+)', details)
            pattern = f'^{pattern}$'
            if re.match(pattern, command):
                return details
            else:
                continue

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

    # templates_set = set(templates)
    # extra_commands_set = set(extra_commands)
    # return templates_set, extra_commands_set
    return templates, extra_commands

def parse_config_file_intact(file_path):
    """解析配置文件为命令列表"""
    commands = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 去除前后空格和缩进
            command = line.strip()
            commands.append(command)
    # commands = set(commands)
    return commands

def calculate_match_ratio(result_templates, expected_templates, result_extra_commands, expected_extra_commands):
    """计算翻译的模板序列的匹配度"""
    match_count = 0
    error_templates = []
    for result_template in result_templates:
        if result_template in expected_templates:
            match_count += 1
            # expected_templates.remove(result_template)
        else:
            error_templates.append(result_template)

    for result_extra_command in result_extra_commands:
        if result_extra_command in expected_extra_commands:
            match_count += 1
            # expected_extra_commands.remove(result_extra_command)
        else:
            error_templates.append(result_extra_command)


    return match_count, (len(result_templates) + len(result_extra_commands)), error_templates


target_vendor = 'HUAWEI'
cisco_huawei_config_dir = './exper_data/cisco_translated_config_with_mapping_examined/HUAWEI'
# cisco_huawei_config_dir = './exper_data/cisco_translated_config/HUAWEI'


cisco_to_huawei_config_files = [f for f in os.listdir(cisco_huawei_config_dir) if f.endswith('.txt')]
huawei_real_config_dir = './exper_data/HUAWEI'

config_model = f'../dataset_multi_vendor_config/config_model/{target_vendor}.json'
config_model = load_config_model(config_model)

total_match_score = 0
total_match_account = 0

total_intact_match_score = 0
total_intact_match_account = 0
file_count = len(cisco_to_huawei_config_files)

for file_name in cisco_to_huawei_config_files:
    file_result = os.path.join(cisco_huawei_config_dir, file_name)
    file_expected = os.path.join(huawei_real_config_dir, file_name)

    # 解析配置文件
    result_templates, result_extra_command = parse_config_file(file_result, config_model)
    result_commands = parse_config_file_intact(file_result)

    expected_templates, expected_extra_command = parse_config_file(file_expected, config_model)
    expected_commands = parse_config_file_intact(file_expected)

    # 计算匹配度
    match_score, match_account, error_templates = calculate_match_ratio(result_templates, expected_templates, result_extra_command, expected_extra_command)
    intact_match_score, intact_match_account, error_commands = calculate_match_ratio(result_commands, expected_commands, [], [])
    total_match_score += match_score
    total_match_account += match_account

    total_intact_match_score += intact_match_score
    total_intact_match_account += intact_match_account


# 计算并输出平均匹配度
average_match_ratio = total_match_score / total_match_account if total_match_account > 0 else 0
average_intact_match_ratio = total_intact_match_score / total_intact_match_account if file_count > 0 else 0
print(f"\nAverage Match Ratio: {average_match_ratio:.2f}")
print(f"\nAverage intact Match Ratio: {average_intact_match_ratio:.2f}")


# Average Exact Match Ratio: 0.70
# Average Tree Match Ratio: 0.91

'''
Average Match Ratio: 0.67

Average intact Match Ratio: 0.64
'''
