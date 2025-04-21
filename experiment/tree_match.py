# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:28
@Auth ： xiaolongtuan
@File ：tree_match.py
"""
import ast
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
            if command.startswith(('#', '!', '*', '/*', '*/')): # 注释行
                continue
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
    for expected_template in expected_templates:
        if expected_template in result_templates:
            match_count += 1
        else:
            error_templates.append(expected_template)

    for expected_extra_command in expected_extra_commands:
        if expected_extra_command in result_extra_commands:
            match_count += 1
            # expected_extra_commands.remove(result_extra_command)
        else:
            error_templates.append(expected_extra_command)

    return match_count, (len(expected_templates) + len(expected_extra_commands)), error_templates


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


def get_all_templates(data):
    templates = []

    def dfs(data:dict):
        for key, value in data.items():
            if isinstance(value, dict):
                dfs(value)
            elif key == 'template':
                templates.append(value)
    dfs(data)
    return templates

def cul_grammatical_accuracy_with_json(translated_dir, real_dir, config_files):
    '''
    直接使用保存的template和label对应的json文件进行匹配，不实用config_model
    real_dir="./exper_data/vendor/"
    '''

    total_match_score = 0
    total_match_account = 0
    for file_name in config_files:
        device_name= os.path.splitext(file_name)[0]

        trans_templates = json.load(open(os.path.join(translated_dir, f"{device_name}_temp.json")))
        expected_json = os.path.join(real_dir, f"{device_name}.json")
        expected_templates = get_all_templates(json.load(open(expected_json)))

        match_score, match_account, error_templates = calculate_match_ratio(trans_templates,
                                                                            expected_templates,
                                                                            [],
                                                                            [])
        total_match_score += match_score
        total_match_account += match_account
    average_match_ratio = total_match_score / total_match_account if total_match_account > 0 else 0
    return average_match_ratio

def grammatical_match(device_name, match_rule, real_dir, config_model:{}):
    expected_json = os.path.join(real_dir, f"{device_name}.json")
    expected_templates = get_all_templates(json.load(open(expected_json)))

    error_mapping_rules = defaultdict(set)
    error_mapping_rules_count = defaultdict(int)

    for map_rule_str in match_rule.keys():
        match_rule = ast.literal_eval(map_rule_str)
        target_template_matchs = match_rule[1]
        if isinstance(target_template_matchs[0], list):
            for target_match in target_template_matchs:
                if target_match[2] not in expected_templates:
                    error_mapping_rules[match_rule[0]].add(target_match[2])
                    error_mapping_rules_count[match_rule[0]] += 1
        else:
            if target_template_matchs == '':
                continue
            if target_template_matchs not in expected_templates:
                error_mapping_rules[match_rule[0]].add(target_template_matchs)
                error_mapping_rules_count[match_rule[0]] += 1
    return error_mapping_rules, error_mapping_rules_count



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
    vendors = ['Juniper']
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

            command_accuracy = cul_command_accuracy(translated_config_dir, real_config_dir, trannlated_config_files)
            print(command_accuracy)

'''
Average Match Ratio: 0.67
Average intact Match Ratio: 0.64
'''
