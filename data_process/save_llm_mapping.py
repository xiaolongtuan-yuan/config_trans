# -*- coding: utf-8 -*-
"""
@Time ： 2025/6/16 12:33
@Auth ： xiaolongtuan
@File ：save_llm_mapping.py
"""
import os
import json
from collections import defaultdict

# 定义目标目录
name = 'translated_config_with_all_data_2800'
data_set = 'valid_data_100_from_all'
source_dir = f"../experiment/exper_data/{name}/{data_set}"
vendor  = ['Cisco', 'HUAWEI', 'Juniper']

target_dir = f'../dataset_multi_vendor_config/mapping_template_library/llm_mapping'
os.makedirs(target_dir, exist_ok=True)

for source in vendor:
    for target in vendor:
        if source != target:
            llm_mapping = defaultdict(set)
            source_path = os.path.join(source_dir, source, target)

            for file in os.listdir(source_path):
                if file.endswith("_trans_mapping.json"):
                    file_path = os.path.join(source_path, file)
                    try:
                        # 打开并读取 JSON 文件
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if "llm_right_trans_mapping" in data:
                                # 将 llm_right_trans_mapping 的值添加到集合中
                                for item in data["llm_right_trans_mapping"]:
                                    llm_mapping[item[0]].add(item[1])
                    except Exception as e:
                        print(f"处理文件 {file_path} 时出错: {e}")
            print(f'{source}->{target}:{len(llm_mapping)}')
            for key, value in llm_mapping.items():
                llm_mapping[key] = list(value)
            with open(os.path.join(target_dir, f'{source}_{target}.json'), 'w', encoding='utf-8') as f:
                json.dump(llm_mapping, f, ensure_ascii=False, indent=4)