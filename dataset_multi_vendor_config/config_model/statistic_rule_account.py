# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/7 16:38
@Auth ： xiaolongtuan
@File ：statistic_rule_account.py
"""
import json
import os


def count_rules(obj):
    count = 0
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, dict):
                if "template" in value:
                    count += 1
                count += count_rules(value)
            elif isinstance(value, list):
                for item in value:
                    count += count_rules(item)
    elif isinstance(obj, list):
        for item in obj:
            count += count_rules(item)
    return count

result = {}
# 遍历different_scale目录下的json文件，统计每个文件中的规则数量
directory = "./different_scale"
for filename in os.listdir(directory):
    if filename.endswith(".json"):
        file_path = os.path.join(directory, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            total_rules = count_rules(data)
            result[filename] = total_rules
            print(f"{filename}: {total_rules} rules")
with open("statistic_rule_account.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=4)
