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
        except:
            return False

    return True


def main():
    # 创建输出目录
    output_base = 'exper_data'
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    for vendor in vendors:
        os.makedirs(os.path.join(output_base, vendor), exist_ok=True)

    # 获取Cisco目录下的所有json文件
    cisco_path = '../dataset_multi_vendor_config/Json_config/Cisco'
    all_files = [f for f in os.listdir(cisco_path) if f.endswith('.json')]

    # 筛选有效文件
    valid_devices = []
    for file in all_files:
        device_name = Path(file).stem
        if validate_json_files(device_name):
            valid_devices.append(device_name)
            if len(valid_devices) >= 600:
                break

    # 复制有效文件到实验数据集目录
    for device in valid_devices:
        for vendor in vendors:
            src = os.path.join('../dataset_multi_vendor_config/Json_config', vendor, f"{device}.json")
            dst = os.path.join(output_base, vendor, f"{device}.json")
            shutil.copy(src, dst)

    print(f"成功筛选并复制了{len(valid_devices)}个设备的配置文件到实验数据集目录")


if __name__ == '__main__':
    main()