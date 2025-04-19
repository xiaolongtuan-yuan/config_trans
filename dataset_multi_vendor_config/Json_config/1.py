# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/25 15:01
@Auth ： xiaolongtuan
@File ：1.py
"""
import os

config_num = [100, 500, 1000, 2000]
vendors = ['Juniper']
# 分别选取100，500，1000，2000个配置文件
for vendor in vendors:
    for num in config_num:
        data_source_dir = f'{vendor}_simplified'
        # 读取data_source_dir下的文件列表，选取.json文件，分别选取num个保存起来
        file_list = os.listdir(data_source_dir)
        file_list = [file for file in file_list if file.endswith('.json')]
        file_list = file_list[:num]
        # 保存到data_source_dir下的config_num目录下
        save_dir = f'partition/{vendor}_{num}'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        # 将file_list的文件全部复制到save_dir中
        for file in file_list:
            file_path = os.path.join(data_source_dir, file)
            save_path = os.path.join(save_dir, file)
            os.system(f'cp {file_path} {save_path}')
        print(f'{vendor} {num} done')

