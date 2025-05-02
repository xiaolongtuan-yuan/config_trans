# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/21 22:43
@Auth ： xiaolongtuan
@File ：huawei_cisco_mix_bug.py
"""
import json
import os
import re


def cisco_huawei_mix_bug(directory, error_key):
    non_standard_files = []
    # 遍历指定目录下的所有文件
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        # 只处理文本文件
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if re.search(error_key, content, re.MULTILINE):
                    non_standard_files.append(filename)
    return non_standard_files

# 使用示例
cisco_dir = 'config_data_400/Cisco'
non_standard_files = cisco_huawei_mix_bug(cisco_dir, r'^sysname')
with open("./error_file_record/error_cisco.json", 'w', encoding='utf-8') as f:
    json.dump(non_standard_files, f, ensure_ascii=False, indent=4)
print("不符合Cisco标准的配置文件：", non_standard_files)

huawei_dir = 'config_data_400/HUAWEI'
non_standard_files = cisco_huawei_mix_bug(huawei_dir, r'^hostname')
with open("./error_file_record/error_huawei.json", 'w', encoding='utf-8') as f:
    json.dump(non_standard_files, f, ensure_ascii=False, indent=4)
print("不符合huawei标准的配置文件：", non_standard_files)