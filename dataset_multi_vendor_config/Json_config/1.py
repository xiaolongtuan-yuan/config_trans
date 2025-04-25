# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/25 15:01
@Auth ： xiaolongtuan
@File ：1.py
"""
import json
import os

vendors = ['Juniper']
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
