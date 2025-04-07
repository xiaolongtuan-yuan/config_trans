# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:28
@Auth ： xiaolongtuan
@File ：tree_match.py
"""
import os
import json
import re
from collections import defaultdict

from experiment.syntax_correctness import find_template, load_config_model


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
                    templates.append(template.lower())
                else:
                    extra_commands.append(command.lower())
    return templates, extra_commands


def parse_config_file_intact(file_path):
    """解析配置文件为命令列表"""
    commands = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 去除前后空格和缩进
            command = line.strip()
            if command:
                commands.append(command.lower())
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


def cul_command_accuracy(translated_dir, real_dir, config_files):
    total_command_match_score = 0
    total_command_match_account = 0

    for file_name in config_files:
        file_result = os.path.join(translated_dir, file_name)
        file_expected = os.path.join(real_dir, file_name)

        result_commands = parse_config_file_intact(file_result)
        expected_commands = parse_config_file_intact(file_expected)

        command_match_score, command_match_account, error_commands = calculate_match_ratio(result_commands,
                                                                                         expected_commands,
                                                                                         [],
                                                                                         [])
        total_command_match_score += command_match_score
        total_command_match_account += command_match_account

    average_command_match_ratio = total_command_match_score / total_command_match_account if total_command_match_account > 0 else 0
    return average_command_match_ratio

def cul_grammatical_accuracy(translated_dir, real_dir, config_files, config_model:{}):
    total_match_score = 0
    total_match_account = 0
    for file_name in config_files:
        file_result = os.path.join(translated_dir, file_name)
        file_expected = os.path.join(real_dir, file_name)

        result_templates, result_extra_command = parse_config_file(file_result, config_model)
        expected_templates, expected_extra_command = parse_config_file(file_expected, config_model)

        match_score, match_account, error_templates = calculate_match_ratio(result_templates,
                                                                            expected_templates,
                                                                            result_extra_command,
                                                                            expected_extra_command)
        total_match_score += match_score
        total_match_account += match_account
    average_match_ratio = total_match_score / total_match_account if total_match_account > 0 else 0
    return average_match_ratio

def calculate_param_match_ratio(result_templates:{}, expected_templates:{}, result_extra_commands:[], expected_extra_commands:[]):
    """计算翻译的模板序列的匹配度"""
    match_score = 0
    match_count = 0

    for result_template, result_commands in result_templates.items():
        if result_template in expected_templates:
            for result_command in result_commands:
                if result_command in expected_templates[result_template]:
                    match_score += 1
                match_count += 1

    for result_extra_command in result_extra_commands:
        if result_extra_command in expected_extra_commands:
            match_count += 1
            match_score += 1

    return match_score, match_count

def cul_param_accuracy(translated_dir, real_dir, config_files, config_model: {}):
    def parse_config_file(file_path, config_model):
        """解析配置文件为模板序列"""
        templates = defaultdict(list)
        extra_commands = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # 去除前后空格和缩进
                command = line.strip()
                if command:
                    template = find_template(command, config_model)
                    if template:
                        templates[template.lower()].append(command.lower())
                    else:
                        extra_commands.append(command.lower())
        return templates, extra_commands

    total_match_score = 0
    total_match_ccount = 0
    for file_name in config_files:
        file_result = os.path.join(translated_dir, file_name)
        file_expected = os.path.join(real_dir, file_name)

        result_templates, result_extra_command = parse_config_file(file_result, config_model)
        expected_templates, expected_extra_command = parse_config_file(file_expected, config_model)

        match_score, match_ccount = calculate_param_match_ratio(result_templates,
                                                                            expected_templates,
                                                                            result_extra_command,
                                                                            expected_extra_command)
        total_match_score += match_score
        total_match_ccount += match_ccount
    average_match_ratio = total_match_score / total_match_ccount if total_match_ccount > 0 else 0
    return average_match_ratio

if __name__ == '__main__':
    scale = 2000
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    translated_config_base = './exper_data/translated_config'

    for source_vendor in ['Cisco']:
        for target_vendor in ['Juniper']:
            if target_vendor == source_vendor:
                continue

            translated_config_dir = os.path.join(translated_config_base, str(scale), source_vendor, target_vendor)
            trannlated_config_files = [f for f in os.listdir(translated_config_dir) if f.endswith('.txt')]
            real_config_dir = f'./exper_data/lable/{target_vendor}'
            # config_model = f'../dataset_multi_vendor_config/config_model/different_scale/{target_vendor}_{scale}.json'
            config_model = f'../dataset_multi_vendor_config/config_model/different_scale/{target_vendor}_{scale}.json'
            config_model = load_config_model(config_model)

            total_match_score = 0
            total_match_account = 0

            total_intact_match_score = 0
            total_intact_match_account = 0
            file_count = len(trannlated_config_files)

            for file_name in trannlated_config_files:
                file_result = os.path.join(translated_config_dir, file_name)
                file_expected = os.path.join(real_config_dir, file_name)

                # 解析配置文件
                result_templates, result_extra_command = parse_config_file(file_result, config_model)
                result_commands = parse_config_file_intact(file_result)

                # 解析标准文件
                expected_templates, expected_extra_command = parse_config_file(file_expected, config_model)
                expected_commands = parse_config_file_intact(file_expected)

                # 计算匹配度
                match_score, match_account, error_templates = calculate_match_ratio(result_templates,
                                                                                    expected_templates,
                                                                                    result_extra_command,
                                                                                    expected_extra_command)
                intact_match_score, intact_match_account, error_commands = calculate_match_ratio(result_commands,
                                                                                                 expected_commands, [],
                                                                                                 [])
                total_match_score += match_score
                total_match_account += match_account

                total_intact_match_score += intact_match_score
                total_intact_match_account += intact_match_account

            # 计算并输出平均匹配度
            average_match_ratio = total_match_score / total_match_account if total_match_account > 0 else 0
            average_intact_match_ratio = total_intact_match_score / total_intact_match_account if file_count > 0 else 0
            print(
                f"Scale {scale}:from {source_vendor} tp {target_vendor} Average Match Ratio: {average_match_ratio:.2f}")
            print(
                f"Scale {scale}:from {source_vendor} tp {target_vendor} Average intact Match Ratio: {average_intact_match_ratio:.2f}")

# Average Exact Match Ratio: 0.70
# Average Tree Match Ratio: 0.91

'''
Average Match Ratio: 0.67
Average intact Match Ratio: 0.64
'''
