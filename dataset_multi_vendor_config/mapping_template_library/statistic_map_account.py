"""
@Time ： 2025/4/7 16:44
@Auth ： xiaolongtuan
@File ：statistic_map_account.py.py
统计映射规则数量
"""
import json
import os

print(os.getcwd())

def count_rules(obj):
    count = 0
    for k, v in obj.items():
        if isinstance(v, list):
            count += len(v)
    return count

result = {}
# 遍历different_scale目录下的json文件，统计每个文件中的规则数量
directory = "./all_data_2800"
# directory = "./multi_module"
vendors = ["Cisco", "Juniper", "HUAWEI"]
for source_vendor in vendors:
    for target_vendor in vendors:
        if source_vendor != target_vendor:
            mapping_library_path = f'all_data_2800/{source_vendor}_{target_vendor}.json'

            llm_mapping_path = f'llm_mapping/{source_vendor}_{target_vendor}.json'
            error_mapping_path = f'error_mapping/{source_vendor}_{target_vendor}.json'
            manual_mapping_path = f'manual_mapping/{source_vendor}_{target_vendor}.json'

            mapping_data = json.load(open(mapping_library_path))
            error_mapping = json.load(open(error_mapping_path))
            for key in error_mapping:
                if key in mapping_data:
                    del mapping_data[key]

            manual_mapping = json.load(open(manual_mapping_path))
            mapping_data.update(manual_mapping)

            llm_mapping = json.load(open(llm_mapping_path))
            mapping_data.update(llm_mapping)
            print(f"{source_vendor}-{target_vendor}: {len(mapping_data)} rules")