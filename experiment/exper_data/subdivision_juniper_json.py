# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/20 12:16
@Auth ： xiaolongtuan
@File ：subdivision_juniper_json.py
"""

import os
import json

from experiment.exper_data_splite import delete_outdate_files


def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data

def subdivision_config(old_config_model:dict, decompose_commands:dict, juniper_model:dict):
    new_config = {}
    for command, detail in old_config_model.items():
        command_words = command.split()
        command_temp = detail["template"]
        sub_model = new_config
        if command_temp in decompose_commands:
            seg = decompose_commands[command_temp]
            segments = seg[0]
            paras = seg[1]
            command_node = juniper_model
            begin = 0
            for k_part in range(len(segments)):
                segment = segments[k_part]
                segment_words = segment.split()
                command_match = ' '.join(command_words[begin:begin+len(segment_words)])
                command_node = command_node[segment]
                if len(segments) == 1:
                    sub_model[command_match] = {"template": segment,
                                          "command": command_match,
                                          "explanation": command_node['explanation'],
                                          "parameters": command_node['parameters']}
                else:
                    sub_model[command_match] = {"template": segment,
                                          "command": command_match,
                                          "explanation": command_node['explanation'],
                                          "parameters": command_node['parameters']}
                    sub_model = sub_model[command_match]
                    begin += len(segment_words)
        else:
            sub_model[command] = detail
    return new_config


def process_juniper_json(json_config):
    processed_json = {}
    for k, v in json_config.items():
        if 'template' in v:
            return None
        if isinstance(v, dict):
            for command, info in v.items():
                processed_json[command] = info
    return processed_json

if __name__ == '__main__':
    juniper_model = load_json_file('../../dataset_multi_vendor_config/config_model/scale388en/Juniper_388.json')
    decompose_command_path = "../../dataset_multi_vendor_config/config_command_node/commands/decompose_Juniper_commands.json"
    decompose_commands = load_json_file(decompose_command_path)

    save_dir = './Juniper_subdivided'
    delete_outdate_files(save_dir)

    for filename in os.listdir('./Juniper'):
        if filename.endswith('.json'):
            file_path = os.path.join('./Juniper', filename)
            old_config = load_json_file(file_path)
            old_config = process_juniper_json(old_config)
            if not old_config:
                continue

            # 使用相同的细分规则处理每个配置文件
            subdivision_model = subdivision_config(old_config, decompose_commands, juniper_model)

            # 保存细分后的配置文件
            save_path = os.path.join(save_dir, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(subdivision_model, f, ensure_ascii=False, indent=4)
