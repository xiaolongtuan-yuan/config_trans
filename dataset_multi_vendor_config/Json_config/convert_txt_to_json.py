# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/21 15:23
@Auth ： xiaolongtuan
@File ：convert_txt_to_json.py
"""
import json
from pathlib import Path

def process_juniper_json(json_config):
    processed_json = {}
    for k, v in json_config.items():
        if isinstance(v, dict) and any(attribute not in v for attribute in ['template', 'command', 'explanation', 'parameters']):
            for command, info in v.items(): # 去除掉第一层 set xxx 命令
                processed_json[command] = info
        else:
            processed_json[k] = v
    return processed_json

def convert_txt_to_json(directory):
    folder = Path(directory)
    txt_files = list(folder.rglob('*.txt'))

    for txt_file in txt_files:
        json_file = txt_file.with_suffix('.json')
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            try:
                # 判断content是否是有效的json字符串
                json_data = json.loads(content)
                # Process Juniper JSON files differently
                if "Juniper" in str(txt_file):
                    json_data = process_juniper_json(json_data)
                json.dump(json_data, open(json_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
            except json.JSONDecodeError:
                print(txt_file)
                continue

# 转换Json_config/Cisco目录下的txt文件为json
for vendor in ['Cisco', 'HUAWEI', "Juniper"]:
    directory = f'./{vendor}'
    convert_txt_to_json(directory)
