# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/25 15:01
@Auth ： xiaolongtuan
@File ：1.py
"""
import json
import os

VALID_FIRST_WORDS = ['set', 'delete', 'rename', 'deactivate', 'activate', 'replace', 'commit']
def juniper_config_filter(config):
    for command in config.keys():
        first_word = command.split()[0] if command else ''
        if first_word not in VALID_FIRST_WORDS:
            print("error junos command: ", command)
            return False
    return True

vendors = ['Juniper', 'Cisco', 'HUAWEI']
error_file_list = {}
for vendor in vendors:
    data_source_dir = f'{vendor}'
    error_file_list[vendor] = []
    file_list = os.listdir(data_source_dir)
    file_list = [file for file in file_list if file.endswith('.txt')]
    for file in file_list:
        file_path = os.path.join(data_source_dir, file)
        with open(file_path, 'r') as f:
            try:
                content = f.read()
                config = json.loads(content)
                if 'error' in content:
                    print("error in json file: ", file_path)
                    error_file_list[vendor].append(file_path)
                if len(config) <= 0:
                    print("null json file: ", file_path)
                    error_file_list[vendor].append(file_path)
                # Add Juniper specific validation
                if vendor == 'Juniper' and not juniper_config_filter(config):
                    print("invalid Juniper command in file: ", file_path)
                    error_file_list[vendor].append(file_path)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {file_path}: {e}")
                error_file_list[vendor].append(file_path)
                continue
    for file_path in error_file_list[vendor]: # 删除这些错误文件
        device_name = os.path.splitext(file_path)[0]
        if os.path.exists(device_name + '.txt'):
            os.remove(device_name + '.txt')
        if os.path.exists(device_name + '.json'):
            os.remove(device_name + '.json')
print(f"Error files: {error_file_list}")
with open(f"json_errors.json", 'w') as f:
    json.dump(error_file_list, f)
