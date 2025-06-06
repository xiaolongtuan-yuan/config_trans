# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/22 13:40
@Auth ： xiaolongtuan
@File ：splite_test_dataset.py
"""
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm
from src.A_LLM_Parse_Config import process_file, prompt_massage_for_vendors, parse_config, save_parsed_config, \
    load_client, splite_config

VALID_FIRST_WORDS = ['set', 'delete', 'rename', 'deactivate', 'activate', 'replace', 'commit']
llm_tasks = []
executor = ThreadPoolExecutor(max_workers=10)
model_name = "deepseek-chat"
client = load_client(model_name)

def juniper_config_filter(config):
    for command in config.keys():
        first_word = command.split()[0] if command else ''
        if first_word not in VALID_FIRST_WORDS:
            print("error junos command: ", command)
            return False
    return True

def check_filename(dir_order, file_name):
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    base_path = '../dataset_multi_vendor_config/Json_config'
    for vendor in vendors:
        text_path = f'../syntactic_check/config_data_{dir_order}/{vendor}_config/{vendor}_{file_name}/configs/{file_name}.cfg'
        file_path = os.path.join(base_path, vendor, f"{file_name}.json")
        if not os.path.exists(file_path):
            print(f"json file {file_path} not exist")
            prompt, messages = prompt_massage_for_vendors(vendor)
            config = open(text_path, 'r', encoding='utf-8').read()
            config_chunks = splite_config(config, max_length=15)
            task = executor.submit(parse_config, client, model_name, prompt, messages, config_chunks)
            llm_tasks.append((file_path, task))
            return True
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

    lable_base_dirs = ["config_data_400",
                       "config_data_800",
                       "config_data_1200",
                       "config_data_2000",
                       "config_data_2800"]
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

    dir_orders = ['2000']
    for dir_order in dir_orders:
        print(f"begin {dir_order}")
        test_filenames= json.load(open( f'../syntactic_check/config_data_{dir_order}/error_info/config_summary.json'))['test_config']['config']
        finished = 0
        for test_filename in tqdm(test_filenames):
            test_filename = test_filename.split('.')[0]
            if not check_filename(dir_order, test_filename):
                print(f"error file {test_filename} not exist")
                continue
            for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
                os.makedirs(f"../experiment/test_dataset/test_data_{dir_order}/text_config/{vendor}", exist_ok=True)
                os.makedirs(f"../experiment/test_dataset/test_data_{dir_order}/command_tree/{vendor}", exist_ok=True)

                text_path = f'../syntactic_check/config_data_{dir_order}/{vendor}_config/{vendor}_{test_filename}/configs/{test_filename}.cfg'
                target_path = os.path.join(f"../experiment/test_dataset/test_data_{dir_order}/text_config/{vendor}", f"{test_filename}.txt")
                if os.path.exists(text_path) and not os.path.exists(target_path):
                    shutil.copy(text_path, target_path)

                command_tree_path = os.path.join('../dataset_multi_vendor_config/Json_config', vendor, f"{test_filename}.json")
                target_command_tree_path = os.path.join(f"../experiment/test_dataset/test_data_{dir_order}/command_tree/{vendor}", f"{test_filename}.json")
                if os.path.exists(command_tree_path) and not os.path.exists(target_command_tree_path):
                    shutil.copy(command_tree_path, target_command_tree_path)
            finished += 1

        for file_path, task in tqdm(llm_tasks):
            result = task.result()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
        print(f'splite {finished} {dir_order} test files')





