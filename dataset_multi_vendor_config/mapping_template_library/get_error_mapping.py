# -*- coding: utf-8 -*-
"""
@Time ： 2025/5/12 20:46
@Auth ： xiaolongtuan
@File ：get_error_mapping.py
"""
import json

def load_mapping_lib(source_vendor, target_vendor):
    with open(f"./multi_module/{source_vendor}_{target_vendor}.json", "r", encoding="utf-8") as f:
        mapping_lib = json.load(f)
    with open(f"./manual_mapping/{source_vendor}_{target_vendor}.json", "r", encoding="utf-8") as f:
        manual_mapping = json.load(f)
    mapping_lib.update(manual_mapping)
    return mapping_lib

vendors = ['Cisco', 'HUAWEI', 'Juniper']
for source_vendor in vendors:
    for target_vendor in vendors:
        if source_vendor == target_vendor:
            continue
        print(f"start {source_vendor} to {target_vendor}")
        to_mapping_lib = load_mapping_lib(source_vendor, target_vendor)
        from_mapping_lib = load_mapping_lib(target_vendor, source_vendor)
        for key,
