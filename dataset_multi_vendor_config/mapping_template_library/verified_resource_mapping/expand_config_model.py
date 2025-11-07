#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从验证规则中提取命令并扩充配置模型
"""

import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

from tqdm import tqdm

from data_process.rearrange_command_tree import LLM_Model

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from src.B_json_simplify import simplify_json
from src.C_Model_growth import merge_models, load_json_file, save_json_file

llm_model = LLM_Model('deepseek-chat')


def load_json_file(file_path: str) -> Dict:
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"警告: 无法加载文件 {file_path}: {e}")
        return {}


def extract_commands_from_rules(rule_file_path: str) -> Set[str]:
    """
    从规则文件中提取指定供应商的所有命令
    
    Args:
        rule_file_path: 规则文件路径
        vendor: 供应商名称 (Cisco/HUAWEI)
        
    Returns:
        命令集合
    """
    rules = load_json_file(rule_file_path)
    source_commands = set()

    # 提取源命令 (Cisco命令)
    for source_command in rules.keys():
        source_command = source_command.strip().split('\n')
        source_commands = source_commands | set(source_command)

    # 提取目标命令 (HUAWEI命令)
    target_commands = set()
    for mappings in rules.values():
        for mapping in mappings:
            trans_command = mapping.get('trans_command', '').strip().split('\n')
            target_commands = target_commands | set(trans_command)

    return '\n'.join(source_commands), '\n'.join(target_commands)


def check_missing_commands(commands: Set[str], config_model: Dict) -> Set[str]:
    """
    检查配置模型中缺失的命令
    
    Args:
        commands: 命令集合
        config_model: 配置模型
        
    Returns:
        缺失的命令集合
    """
    missing_commands = set()

    def find_template_in_model(command: str, model: Dict) -> bool:
        """递归查找命令模板"""
        for template, details in model.items():
            if isinstance(details, dict) and 'template' in details:
                # 递归查找子模板
                if find_template_in_model(command, details):
                    return True

                # 使用正则表达式匹配模板
                pattern = re.sub(r"\[[^\]]+\]", r'(\\S+)', details['template'])
                pattern = f'^{pattern}$'
                try:
                    if re.match(pattern, command):
                        return True
                except re.error:
                    continue
        return False

    for command in commands:
        if not find_template_in_model(command, config_model):
            missing_commands.add(command)

    return missing_commands


def find_template(command, config_model):
    for template, details in config_model.items():
        if isinstance(details, dict) and 'template' in details:
            sub_template = find_template(command, details)
            if sub_template:
                return sub_template

            pattern = re.sub(r"\[[^\]]+\]", r'(\\S+)', details['template'])
            pattern = f'^{pattern}$'
            try:
                if re.match(pattern, command):
                    return {
                        "template": details['template'],
                        "command": command,
                        "explanation": details['explanation'],
                        "parameters": details['parameters'],
                    }
                else:
                    continue
            except re.error:
                continue
    return None


def parse_config_file(config_str, config_model):
    tasks = []
    lines = config_str.split('\n')
    if not lines:
        return {}
    root = {}
    stack = [(0, root)]  # (缩进级别, 当前字典)
    for line in lines:
        if not line.strip() or line.strip().startswith(('#', '!', '*', '/*', '*/', '/')):
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        template = find_template(content, config_model)
        if not template:
            future = llm_model.parse_command(content)
            template = {
                "template": content,
                "command": content,
                "explanation": '',
                "parameters": [],
            }
            tasks.append((future, template))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            root[content] = template
            stack.append((indent, root[content]))
            continue
        parent_indent, parent_dict = stack[-1]
        parent_dict[content] = template
        stack.append((indent, parent_dict[content]))
    return root, tasks


def expand_config_model(
        rule_file_path: str,
        config_model_path: str,
        temp_dir: str,
        simplified_source_config_json_path = None,
        simplified_target_config_json_path = None
):
    """
    扩充配置模型
    
    Args:
        vendor: 供应商名称
        rule_file_path: 规则文件路径
        config_model_path: 配置模型路径
        temp_dir: 临时目录
    """
    print(f"开始扩充配置模型...")
    # 1. 加载配置模型
    source_config_model = load_json_file(f"{config_model_path}/Cisco.json")
    target_config_model = load_json_file(f"{config_model_path}/HUAWEI.json")

    if not simplified_source_config_json_path or not simplified_target_config_json_path:
        # 2. 从规则中提取命令
        source_commands, target_commands = extract_commands_from_rules(rule_file_path)

        # 3. 创建临时配置文件
        with open(f"{temp_dir}/Cisco_commands.txt", 'w', encoding='utf-8') as f:
            f.write(source_commands)
        with open(f"{temp_dir}/HUAWEI_commands.txt", 'w', encoding='utf-8') as f:
            f.write(target_commands)

        # 采用之间的方法，并发的给他们解析了：
        source_config_json, source_tasks = parse_config_file(source_commands, source_config_model)
        for future, template in tqdm(source_tasks, "cisco LLM解析结果"):
            result = future.result()
            template.update(result)

        save_json_file(source_config_json, f"{temp_dir}/Cisco_commands_json.json")
        print(f"cisco LLM解析结果已保存!")

        simplified_source_config_json = simplify_json(source_config_json)
        save_json_file(simplified_source_config_json, f"{temp_dir}/Cisco_simplified_commands.json")
        print("cisco 配置模型简化完成!")

        target_config_json, target_tasks = parse_config_file(target_commands, target_config_model)
        for future, template in tqdm(target_tasks, "huawei LLM解析结果"):
            result = future.result()
            template.update(result)
        save_json_file(target_config_json, f"{temp_dir}/HUAWEI_commands.json")
        print(f"huawei LLM解析结果已保存!")

        simplified_target_config_json = simplify_json(target_config_json)
        save_json_file(simplified_target_config_json, f"{temp_dir}/HUAWEI_simplified_commands.json")
        print("huawei 配置模型简化完成!")
    else:
        simplified_source_config_json = load_json_file(simplified_source_config_json_path)
        simplified_target_config_json = load_json_file(simplified_target_config_json_path)

    # 7. 合并到现有配置模型
    print("合并到现有Cisco配置模型...")
    try:
        # 使用C_Model_growth.py中的合并逻辑
        merged_source_model = merge_models(
            source_config_model,
            simplified_source_config_json,
            {},
            defaultdict(int)
        )

        # 保存扩充后的配置模型
        save_json_file(merged_source_model, f"{temp_dir}/Cisco.json")
        print(f"扩充后的Cisco配置模型已保存")

        ####################
        merged_target_model = merge_models(
            target_config_model,
            simplified_target_config_json,
            {},
            defaultdict(int)
        )
        save_json_file(merged_target_model, f"{temp_dir}/HUAWEI.json")
        print(f"扩充后的HUAWEI配置模型已保存")

    except Exception as e:
        print(f"配置模型合并失败: {e}")
        return

    print(f"配置模型扩充完成!")


def main():
    """主函数"""
    # 配置路径
    rule_file_path = "dataset_multi_vendor_config/verified_resources/rule.json"
    config_model_dir = "dataset_multi_vendor_config/config_model/all_data_2800"
    temp_dir = "dataset_multi_vendor_config/mapping_template_library/verified_resource_mapping/temp_expansion"

    os.makedirs(temp_dir, exist_ok=True)

    expand_config_model(
        rule_file_path=rule_file_path,
        config_model_path=config_model_dir,
        temp_dir=temp_dir,
        # simplified_source_config_json_path=f"{temp_dir}/Cisco_simplified_commands.json",
        # simplified_target_config_json_path=f"{temp_dir}/HUAWEI_simplified_commands.json"
    )


if __name__ == "__main__":
    main()
