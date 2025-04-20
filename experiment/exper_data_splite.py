# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:33
@Auth ： xiaolongtuan
@File ：exper_data_splite.py
"""
'''
从dataset_multi_vendor_config/Json_config/Cisco 中读取所有json文件，并提取出其中的文件名列表，一个文件名对应一个设备名，从该列表中抽取出400个有效文件,要求：
1. 能够分别在dataset_multi_vendor_config/Json_config/HUAWEI 和dataset_multi_vendor_config/Json_config/Juniper 中存在对应的json文件，也就是一个设备名能够对应3个供应商配置文件
2. 每个设备的三个供应商配置json能够正确加载，且其中内容没有包含‘error’字符串
将这400个设备的有效文件分别保存为3个文件夹下，对应3个供应商作为实验数据集
'''
import os
import json
import shutil
from pathlib import Path

VALID_FIRST_WORDS = ['set', 'delete', 'rename', 'deactivate', 'activate','replace','commit']

def process_juniper_json(json_config):
    processed_json = {}
    for k, v in json_config.items():
        if 'template' in v:
            del v['template']
        if isinstance(v, dict):
            for command, info in v.items():
                processed_json[command] = info
    return processed_json


def juniper_config_filter(config):
    config = process_juniper_json(config)
    with open('../dataset_multi_vendor_config/config_model/Juniper_error_command.json', 'r') as f:
        juniper_error_commands = json.load(f)
    if len(config) < 3:  # 命令太少了，可能是错误的配置
        return False
    for command in config.keys():
        if command in juniper_error_commands:
            return False
        first_word = command.split()[0] if command else ''
        if first_word not in VALID_FIRST_WORDS:
            return False

    return True


def validate_json_files(device_name):
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    base_path = '../dataset_multi_vendor_config/Json_config'

    # 检查三个供应商的配置文件是否存在
    for vendor in vendors:
        file_path = os.path.join(base_path, vendor, f"{device_name}.json")
        if not os.path.exists(file_path):
            return False

    # 检查文件内容是否有效
    for vendor in vendors:
        file_path = os.path.join(base_path, vendor, f"{device_name}.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                if 'error' in str(content):
                    return False
                if vendor == 'Juniper':
                    # 检测其中是否有错误行
                    if not juniper_config_filter(content):
                        print(device_name)
                        return False
        except:
            return False

    return True


def delete_outdate_files(file_dir):
    os.makedirs(file_dir, exist_ok=True)
    # 清空目录下的所有文件
    for file in os.listdir(file_dir):
        file_path = os.path.join(file_dir, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")


def find_lable_path(device_name, vendor):
    lable_base_dirs = ["config_data_1-400",
                       "config_data_401-800",
                       "config_data_801-1200",
                       "config_data_1600_1999",
                       "config_data_2400-2889"]
    for lable_base_dir in lable_base_dirs:
        file_path = os.path.join("../dataset_multi_vendor_config",lable_base_dir, vendor, f"{device_name}.txt")
        if os.path.exists(file_path):
            if vendor == 'Juniper':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = [line for line in f.read().splitlines()
                                   if line.strip() and not line.strip().startswith(('#', '!', '*', '/*', '*/'))]
                    first_word = content[0].split()[0] if content else ''
                    if first_word not in VALID_FIRST_WORDS:
                        continue
            return file_path
    return None

def main():
    # 创建输出目录
    output_base = 'exper_data'
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    for vendor in vendors:
        os.makedirs(os.path.join(output_base, vendor), exist_ok=True)
        delete_outdate_files(os.path.join(output_base, vendor))

        os.makedirs(os.path.join(output_base, 'lable', vendor), exist_ok=True)
        delete_outdate_files(os.path.join(output_base, 'lable', vendor))

    # 获取Cisco目录下的所有json文件
    cisco_path = '../dataset_multi_vendor_config/Json_config/Cisco'
    all_files = [f for f in os.listdir(cisco_path) if f.endswith('.json')]

    # 筛选有效文件
    valid_devices = []
    for file in all_files:
        device_name = Path(file).stem
        if validate_json_files(device_name):
            valid_devices.append(device_name)
            if len(valid_devices) >= 800:
                break

    print(len(valid_devices))
    exper_data = 0
    for device in valid_devices:
        has_lable = True
        for vendor in vendors:
            lable_path = find_lable_path(device, vendor)
            if lable_path:
                shutil.copy(lable_path, os.path.join(output_base, 'lable', vendor, f"{device}.txt"))
            else:
                has_lable = False
                break

        if has_lable:
            for vendor in vendors:
                src = os.path.join('../dataset_multi_vendor_config/Json_config', vendor, f"{device}.json")
                dst = os.path.join(output_base, vendor, f"{device}.json")
                shutil.copy(src, dst)
            exper_data += 1
            if exper_data == 600:
                break

    print(f"成功筛选并复制了{exper_data}个设备的配置文件到实验数据集目录")

if __name__ == '__main__':
    main()
