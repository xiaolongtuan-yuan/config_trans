# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:30
@Auth ： xiaolongtuan
@File ：syntax_correctness.py
"""
import json
import os
import re

def parse_config(config_str):
    lines = config_str.strip().split('\n')
    if not lines:
        return {}

    root = {}
    stack = [(0, root)]  # (缩进级别, 当前字典)

    for line in lines:
        if not line.strip():
            continue

        # 计算缩进级别
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        # 弹出所有大于当前缩进级别的节点
        while stack and stack[-1][0] >= indent:
            stack.pop()

        # 如果栈为空，说明第一行有缩进，直接添加到根节点
        if not stack:
            root[content] = {}
            stack.append((indent, root[content]))
            continue

        # 获取父节点
        parent_indent, parent_dict = stack[-1]

        # 添加当前节点
        parent_dict[content] = {}

        # 将当前节点压入栈
        stack.append((indent, parent_dict[content]))
    return root

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

def tree_match(parent_command, child_command, config_model):
    for template, details in config_model.items():
        # 使用正则表达式匹配模板
        pattern = re.sub(r'\[parameter\d+\]', r'[\\w\\s]+', template)
        if re.match(pattern, parent_command):
            if isinstance(details, dict) and 'template' in details:
                sub_template = find_template(child_command, details)
                if sub_template:
                    return True
                else:
                    return False
        if isinstance(details, dict) and 'template' not in details:
            match_res = tree_match(parent_command, child_command, details)
            if match_res:
                return True
    return False

def cul_syntax_score(parsed_config, config_model, syntax_score=0, match_times=0):
    for parent_command, child_commands in parsed_config.items():
        for child_command, grandson_command in child_commands.items():
            if tree_match(parent_command, child_command, config_model):
                syntax_score += 1
            match_times += 1
            sub_syntax_score, sub_match_time = cul_syntax_score({child_command: grandson_command}, config_model)
            syntax_score += sub_syntax_score
            match_times += sub_match_time
    return syntax_score, match_times


if __name__ == '__main__':
    target_vendor = 'HUAWEI'
    cisco_huawei_config_dir = './exper_data/cisco_translated_config_with_mapping_examined/HUAWEI'
    cisco_to_huawei_config_files = [f for f in os.listdir(cisco_huawei_config_dir) if f.endswith('.txt')]

    config_model = f'../dataset_multi_vendor_config/config_model/{target_vendor}.json'
    config_model = load_config_model(config_model)

    total_syntax_ratio = 0
    for file_name in cisco_to_huawei_config_files:
        file_path = os.path.join(cisco_huawei_config_dir, file_name)
        file_content = open(file_path, 'r', encoding='utf-8').read()
        parsed_config = parse_config(file_content)
        total_syntax_score, total_match_times = cul_syntax_score(parsed_config, config_model)
        if total_match_times == 0:
            total_syntax_ratio += 1
            continue
        total_syntax_ratio += total_syntax_score / total_match_times

    avarage_syntax_score = total_syntax_ratio / len(cisco_to_huawei_config_files)
    print(f'avage syntax ratio: {avarage_syntax_score}')




