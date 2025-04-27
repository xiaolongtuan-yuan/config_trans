# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/24 14:00
@Auth ： xiaolongtuan
@File ：splite_train_dataset.py
"""
import json
import os
import shutil
from tqdm import tqdm

def process_juniper_json(json_config):
    processed_json = {}
    for k, v in json_config.items(): # 去除掉第一层 set xxx 命令
        if isinstance(v, dict):
            for command, info in v.items():
                if isinstance(info, dict):
                    processed_json[command] = info
    return processed_json

def process_config_error_line(source_path, target_path, vendor_error_info):
    with open(source_path, 'r', encoding='utf-8') as file:
        config_content = file.read()

    file_name = source_path.split('/')[-1]
    file_error_lines = []
    if file_name in vendor_error_info:
        if 'line' not in vendor_error_info[file_name]:
            raise Exception(f'{file_name} must be ruled out')
        file_error_lines += vendor_error_info[file_name]['line']
    # 去除掉config_content中的error_line
    lines = config_content.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        if i not in file_error_lines:
            new_lines.append(line)
    with open(target_path, 'w', encoding='utf-8') as file:
        file.write('\n'.join(new_lines))
    return

def delete_error_command_tree(node, error_commands:[]):
    new_command_tree = {}
    for k, v in node.items():
        if isinstance(v, dict):
            v = delete_error_command_tree(v, error_commands)
            if 'command' in v:
                if v['command'] not in error_commands:
                    new_command_tree[k] = v
        else:
            new_command_tree[k] = v
    return new_command_tree


def process_command_tree_error_line(source_path, target_path, vendor_error_info):
    with open(source_path, 'r', encoding='utf-8') as file:
        old_config_content = json.load(file)
        if 'Juniper' in target_path and len(next(iter(old_config_content)).split(' ')) <= 2:
            config_content = process_juniper_json(old_config_content)
        else:
            config_content = old_config_content

    file_name = source_path.split('/')[-1]
    file_name = file_name.split('.')[0] + '.txt'
    file_error_texts = []
    if file_name in vendor_error_info:
        if 'line' not in vendor_error_info[file_name]:
            raise Exception(f'{file_name} must be ruled out')
        file_error_texts += vendor_error_info[file_name]['text']
    right_command_tree = delete_error_command_tree(config_content, error_commands=file_error_texts)
    with open(target_path, 'w', encoding='utf-8') as file:
        json.dump(right_command_tree, file, indent=4, ensure_ascii=False)
    return


if __name__ == '__main__':
    # 删除目录../experiment/test_dataset
    # if os.path.exists('../experiment/train_dataset'):
    #     shutil.rmtree('../experiment/train_dataset')
    for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
        os.makedirs(f'../experiment/train_dataset/text_config/{vendor}', exist_ok=True)
        os.makedirs(f'../experiment/train_dataset/command_tree/{vendor}', exist_ok=True)

    train_filenames = json.load(open( f'../syntactic_check/error_info/config_summary.json'))['all_config']['config']
    finished = 0
    error_infos = {}
    for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
        if vendor == "HUAWEI":
            error_infos[vendor] = {}
        else:
            with open(f'../syntactic_check/error_info/{vendor}_error_syntax.json', 'r') as file:
                error_info = json.load(file)
            error_infos[vendor] = error_info

    for test_filename in tqdm(train_filenames):
        test_filename = test_filename.split('.')[0]
        for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
            text_path = f'../dataset_multi_vendor_config/config_data_1-400/{vendor}/{test_filename}.txt'
            target_path = f'../experiment/train_dataset/text_config/{vendor}/{test_filename}.txt'
            try:
                process_config_error_line(text_path, target_path, error_infos[vendor])  #复制txt文件到目标目录
            except Exception as e:
                print(f'error in {test_filename} {vendor} {e}')  # 直接跳过该文件
                continue

            command_tree_path = f'../dataset_multi_vendor_config/Json_config/{vendor}/{test_filename}.json'
            target_path = f'../experiment/train_dataset/command_tree/{vendor}/{test_filename}.json'
            process_command_tree_error_line(command_tree_path, target_path, error_infos[vendor])  #复制command tree到目标目录

        finished += 1
    print(f'splite {finished} test files')

