import json
import argparse
import glob
from pathlib import Path
import os
from tqdm import tqdm


def merge_nodes(existing_node: dict, new_node: dict):
    """
    将 new_node 合并到 existing_node 中：
    - existing_node 已存在的键值不覆盖（只保留第一次出现节点）；
    - 如果键对应的 value 是一个 dict（子节点），递归合并；
    - 如果是任意其他类型且不存在于 existing_node，则直接添加。
    """
    for key, val in new_node.items():
        # 如果在 existing_node 中没有这个 key，直接添加
        if key not in existing_node:
            existing_node[key] = val
        else:
            # 若都为 dict，则需要递归合并，否则跳过（只保留第一次）
            if isinstance(existing_node[key], dict) and isinstance(val, dict):
                merge_nodes(existing_node[key], val)
            # 其余情况按照“保留第一次出现”的原则，不覆盖 existing_node[key]
    return existing_node

def merge_models(config1, config2):
    """
    递归地将 config2 中不存在于 config1 的节点合并到 config1 中。
    如果 key 存在于 config1 且对应子节点都是字典，则继续合并其子节点；
    如果 key 不存在于 config1，则将 config2[key] 直接插入到 config1；
    如果 key 都存在，但对应的值不是字典，则保持 config1 原值不变（即不覆盖）。
    """
    for key, value in config2.items():
        if key not in config1:
            # 如果 config1 中没有该键，直接插入
            config1[key] = value
        else:
            # 如果 config1 中已经存在这个 key，
            # 且双方都是 dict，则递归合并子节点
            if isinstance(value, dict) and isinstance(config1[key], dict):
                merge_models(config1[key], value)
            # 如果不是 dict，则不覆盖，保持原值。
            # 所以这里什么都不做即可
    return config1


def get_json_filenames(folder_path):
    folder = Path(folder_path)
    json_filenames = [str(file.name) for file in folder.rglob('*.json')]
    return json_filenames


# load JSON fie and load data
def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data


# save JSON fie
def save_json_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as json_file:
        # json.dump(data, json_file, indent=4)
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    # print("JSON文件已保存至{}".format(file_path))


# insert 'template' item into juniper config model
def insert_template(config_model: dict) -> dict:
    for k, sub_dict in config_model.items():
        # 若子项不是 dict，可能是其他值，跳过（通常不应该出现，但做个保护）
        if not isinstance(sub_dict, dict):
            continue

        # 拿到该节点的 template，作为新 key
        template_key = sub_dict.get("template")
        if not template_key:
            # 没有 template 就插入
            sub_dict["template"] = k

        for child_k, child_v in sub_dict.items():
            insert_template({child_k: child_v})

    return config_model


if __name__ == "__main__":
    vendors = ["Cisco", "HUAWEI", "Juniper"]
    project_root = Path(__file__).parent.parent

    # merge the device configuration to the vendor model
    for vendor in vendors:
        folder_path = str(project_root / 'dataset_multi_vendor_config/Json_config/{}_simplified'.format(vendor))
        vendor_model_path = str(project_root / 'dataset_multi_vendor_config/config_model/{}.json'.format(vendor))

        json_files = get_json_filenames(folder_path)
        merge_count = 0
        for json_file in tqdm(json_files, desc="Merged config num"):
            json_config_path = folder_path + '/' + json_file
            # 加载设备配置模型
            try:
                json_config = load_json_file(json_config_path)
            except:
                continue
            # 加载供应商配置模型
            vendor_model = load_json_file(vendor_model_path)
            vendor_model = merge_models(vendor_model, json_config)
            save_json_file(vendor_model, vendor_model_path)
            merge_count += 1
        print(merge_count)


