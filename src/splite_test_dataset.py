# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/22 13:40
@Auth ： xiaolongtuan
@File ：splite_test_dataset.py
"""
import json
import os
import shutil

from torch.optim.rprop import rprop
from tqdm import tqdm

VALID_FIRST_WORDS = ['set', 'delete', 'rename', 'deactivate', 'activate', 'replace', 'commit']
def juniper_config_filter(config):
    for command in config.keys():
        first_word = command.split()[0] if command else ''
        if first_word not in VALID_FIRST_WORDS:
            print("error junos command: ", command)
            return False
    return True

def check_filename(file_name):
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    base_path = '../dataset_multi_vendor_config/Json_config'
    for vendor in vendors:
        file_path = os.path.join(base_path, vendor, f"{file_name}.json")
        if not os.path.exists(file_path):
            print(f"file {file_path} not exist")
            return False
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    content = json.load(f)
                    if 'error' in str(content):
                        print("error in json file: ", file_path)
                        return False
                    if vendor == 'Juniper':
                        # 检测其中是否有错误行
                        if not juniper_config_filter(content):
                            print(file_name)
                            return False
                except:
                    print("error json file: ", file_path)
                    return False

    lable_base_dirs = ["config_data_1-400",
                       "config_data_401-800",
                       "config_data_801-1200",
                       "config_data_1600_1999",
                       "config_data_2400-2889"]
    text_path = None
    for lable_base_dir in lable_base_dirs:
        temp_path = os.path.join("../dataset_multi_vendor_config", lable_base_dir, "Juniper",
                                 f"{test_filename}.txt")
        if os.path.exists(temp_path):
            text_path = temp_path
            break
    if text_path is None:
        return False
    return True

if __name__ == '__main__':
    # 删除目录../experiment/test_dataset
    # if os.path.exists('../experiment/test_dataset'):
    #     shutil.rmtree('../experiment/test_dataset')
    for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
        os.makedirs(f'../experiment/test_dataset/text_config/{vendor}', exist_ok=True)
        os.makedirs(f'../experiment/test_dataset/command_tree/{vendor}', exist_ok=True)
    error_file_list = json.load(open( f'../dataset_multi_vendor_config/error_file_record/error_cisco.json'))
    error_device_list = [file_name.split('.')[0] for file_name in error_file_list]

    test_filenames= json.load(open( f'../syntactic_check/config_data_400/error_info/config_summary.json'))['test_config']['config']
    finished = 0
    for test_filename in tqdm(test_filenames):
        test_filename = test_filename.split('.')[0]
        if test_filename in error_device_list:
            print(test_filename)
            continue
        if not check_filename(test_filename):
            continue
        for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
            if vendor == 'Juniper':
                lable_base_dirs = ["config_data_1-400",
                                   "config_data_401-800",
                                   "config_data_801-1200",
                                   "config_data_1600_1999",
                                   "config_data_2400-2889"]
                for lable_base_dir in lable_base_dirs:
                    text_path = os.path.join("../dataset_multi_vendor_config", lable_base_dir, vendor,
                                             f"{test_filename}.txt")
                    if os.path.exists(text_path):
                        shutil.copy(text_path, os.path.join(f"../experiment/test_dataset/text_config/{vendor}",
                                                            f"{test_filename}.txt"))
                        break
            else:
                text_path = f'../dataset_multi_vendor_config/config_data_1-400/{vendor}/{test_filename}.txt'
                shutil.copy(text_path, os.path.join(f"../experiment/test_dataset/text_config/{vendor}", f"{test_filename}.txt"))

            command_tree_path = os.path.join('../dataset_multi_vendor_config/Json_config', vendor, f"{test_filename}.json")
            if os.path.exists(command_tree_path):
                shutil.copy(command_tree_path, os.path.join(f"../experiment/test_dataset/command_tree/{vendor}", f"{test_filename}.json"))
        finished += 1
    print(f'splite {finished} test files')





