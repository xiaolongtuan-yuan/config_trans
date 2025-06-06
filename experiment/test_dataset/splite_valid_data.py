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


device_list = os.listdir(f'all_data/text_config/Juniper')
total_devices = [device.split('.')[0] for device in device_list]
print(f"Cisco: {len(os.listdir('all_data/text_config/Cisco'))}")
print(f"HUAWEI: {len(os.listdir('all_data/text_config/HUAWEI'))}")
print(f"Juniper: {len(os.listdir('all_data/text_config/Juniper'))}")
target_dir = 'valid_data'

if os.path.exists(target_dir):
    shutil.rmtree(target_dir)
# 从total_devices中随机抽取50个设备
sample_data = random.sample(total_devices, 120)
valid_devices = []

for device in sample_data:
    flag = True
    for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
        command_tree = f'command_tree/{vendor}/{device}.json'
        Json_simplified = f'Json_simplified/{vendor}/{device}.json'
        text_config = f'text_config/{vendor}/{device}.txt'

        for focus_dir in [command_tree, Json_simplified, text_config]:
            if not os.path.exists(os.path.join('all_data', focus_dir)):
                flag = False
                break
    if flag:
        valid_devices.append(device)
        if len(valid_devices) == 100: break

for device in valid_devices:
    for vendor in ['Cisco', 'HUAWEI', 'Juniper', 'Juniper_subdivided']:
        command_tree = f'command_tree/{vendor}/{device}.json'
        Json_simplified = f'Json_simplified/{vendor}/{device}.json'
        text_config = f'text_config/{vendor}/{device}.txt'

        for focus_dir in [command_tree, Json_simplified, text_config]:
            if os.path.exists(os.path.join('all_data', focus_dir)):
                # 复制
                os.makedirs('/'.join(f'{target_dir}/{focus_dir}'.split('/')[:-1]), exist_ok=True)
                os.system(f'cp all_data/{focus_dir} {target_dir}/{focus_dir}')

print(f'sample data: {len(valid_devices)}')




