# -*- coding: utf-8 -*-
"""
@Time ： 2025/5/10 00:27
@Auth ： xiaolongtuan
@File ：splite_valid_data.py
"""
import os
import random
import shutil

random.seed(42)

total_devices = []
total_num = 0
for num in ['400', '1200', '2000', '2800']:
    scale_dir = f'test_data_{num}'
    device_list = os.listdir(f'{scale_dir}/text_config/Cisco')
    device_list = [device.split('.')[0] for device in device_list]
    total_num += len(device_list)
    total_devices.extend(device_list)
total_devices = list(set(total_devices))
print(total_num)
print(len(total_devices))
target_dir = 'all_data'

if os.path.exists(target_dir):
    shutil.rmtree(target_dir)
# 从total_devices中随机抽取50个设备
# valid_devices = random.sample(total_devices, 50)
valid_devices = total_devices
for num in ['400', '1200', '2000', '2800']:
    scale_dir = f'test_data_{num}'
    device_list = os.listdir(f'{scale_dir}/text_config/Cisco')
    device_list = [device.split('.')[0] for device in device_list]
    for device in device_list:
        if device in valid_devices:
            for vendor in ['Cisco', 'HUAWEI', 'Juniper', 'Juniper_subdivided']:
                command_tree = f'command_tree/{vendor}/{device}.json'
                Json_simplified = f'Json_simplified/{vendor}/{device}.json'
                text_config = f'text_config/{vendor}/{device}.txt'
                for focus_dir in [command_tree, Json_simplified, text_config]:
                    if os.path.exists(os.path.join(scale_dir, focus_dir)):
                        # 复制
                        os.makedirs('/'.join(f'{target_dir}/{focus_dir}'.split('/')[:-1]), exist_ok=True)
                        os.system(f'cp {scale_dir}/{focus_dir} {target_dir}/{focus_dir}')



