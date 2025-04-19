"""
@Time ： 2025/4/7 16:44
@Auth ： xiaolongtuan
@File ：statistic_map_account.py.py
"""
import json
import os


def count_rules(obj):
    count = 0
    for k, v in obj.items():
        if isinstance(v, list):
            count += len(v)
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