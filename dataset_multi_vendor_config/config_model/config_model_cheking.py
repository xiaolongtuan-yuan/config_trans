# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/27 16:07
@Auth ： xiaolongtuan
@File ：config_model_cheking.py
"""
# 单独会华为配置进行检查
import json
import os
import re

def load_config_model(config_model_path):
    """加载配置模板"""
    with open(config_model_path, 'r', encoding='utf-8') as f:
        return json.load(f)

config_num = [100, 500, 1000, 2000]
for num in config_num:
    config_model_path = os.path.join(os.path.dirname(__file__), f'different_scale/Cisco_{num}.json')
    config_model = load_config_model(config_model_path)
    # 检查模板是否符合规范,不可以存在template == "[parameter1]"的字典
    for k, v in config_model.items():
        if not isinstance(v, dict):
            print(f"模板{k}的值不是字典类型，不符合规范")
            continue
        template = v.get('template')
        if not template:
            print(f"模板{k}没有'template'字段，不符合规范")
            continue
        if re.search(r'\[.*?\]', template):
            print(f"模板{k}的'template'字段不符合规范，不能包含[parameter1]")
            continue
        if template == k:
            print(f"模板{k}的'template'字段不符合规范，不能等于{k}")
            continue

