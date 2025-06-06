# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/12 16:04
@Auth ： xiaolongtuan
@File ：juniper_translate.py
"""
import json
import re
import pandas as pd
from langchain_community.embeddings import HuggingFaceEmbeddings
from tqdm import tqdm

from data_process.rearrange_command_tree import LLM_Model
from data_process.subdivision_juniper_json import split_parameters
from huawei_test.juniper_trans import view_to_command
from src.F_new_device_configtrans import mapping_library_load, config_matchers_load, Translation_Model, \
    Config_Translater, config_model_load

def find_template(command, config_model, subdivide_model):
    for template, details in config_model.items():
        if isinstance(details, dict) and 'template' in details:
            pattern = re.sub(r"\[[^\]]+\]", r'(\\S+)', details['template'])
            pattern = f'^{pattern}$'
            try:
                if re.match(pattern, command):
                    # subdivision
                    command_words = command.split()
                    segments, paras = split_parameters(template)
                    begin = 0

                    # 处理第一个segment
                    segment = segments[0]
                    segment_words = segment.split()
                    command_match = ' '.join(command_words[begin:begin + len(segment_words)])

                    new_node = {"template": segment,
                                                "command": command_match,
                                                "explanation": subdivide_model[segment]['explanation'],
                                                "parameters": subdivide_model[segment]['parameters']}

                    if len(segments) > 1:
                        begin += len(segment_words)
                        remaining_segment = ' '.join(segments[1:])
                        subdivide_model = subdivide_model[segment]
                        if remaining_segment:
                            remaining_words = command_words[begin:]
                            command_match = ' '.join(remaining_words)
                            if command_match not in new_node:
                                new_node[command_match] = {"template": remaining_segment,
                                                            "command": command_match,
                                                            "explanation": subdivide_model[remaining_segment]['explanation'],
                                                            "parameters": details['parameters'][1:]}
                    return new_node
                else:
                    continue
            except re.error:
                continue
    return None

def parse_config_file(config_str, config_model, subdivide_model):
    tasks = []
    lines = config_str.split('\n')
    if not lines:
        return {}
    root = {}
    stack = [(0, root)]  # (缩进级别, 当前字典)
    for line in lines:
        if not line.strip() or line.strip().startswith(('#', '!', '*', '/*', '*/', '/')):
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        template = find_template(content, config_model, subdivide_model)
        if not template:
            future = llm_model.parse_command(content)
            template = {
                "template": content,
                "command": content,
                "explanation": '',
                "parameters": [],
            }
            tasks.append((future, template))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            root[content] = template
            stack.append((indent, root[content]))
            continue
        parent_indent, parent_dict = stack[-1]
        parent_dict[content] = template
        stack.append((indent, parent_dict[content]))
    return root, tasks

if __name__ == '__main__':
    llm_model = LLM_Model('deepseek-chat')
    source_vendor = "Juniper"
    local_EMmodel_path = '../EmbeddingModel/MiniLM-L6-v2'
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": 'cuda:0'})
    vendors = ["HUAWEI", "Juniper"]
    manual_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/manual_mapping/{{}}_{{}}.json'
    templates_path = f'../dataset_multi_vendor_config/config_command_node/verified_data/{{}}.json'
    mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}.json'
    module_match_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}_module_match.json'
    config_model_dir = f'../dataset_multi_vendor_config/config_model/verified_data/{{}}.json'

    mapping_libraries = mapping_library_load(mapping_library_path, vendors, manual_mapping_path)
    config_matchers = config_matchers_load(templates_path, config_model_dir, module_match_path, vendors)

    translation_llm = Translation_Model('aliyun_deepseek-r1',
                                        config_model_dir=config_model_dir,
                                        vendors=vendors)

    config_models = config_model_load(config_model_dir, vendors)

    config_translater = Config_Translater(mapping_libraries, config_matchers,
                                          translation_llm, embedding_model, config_models)

    # 读取xlsx文件
    df = pd.read_excel('JUNIPER_validation_set(no_answer)v2.xlsx')

    # 遍历每一行数据
    for index, row in tqdm(df.iterrows(), total=len(df)):
        # 这里可以对每一行数据进行处理
        # 例如：打印每一行的数据
        origin_config = str(row['Origin'])
        command_config = view_to_command(origin_config)
        df.at[index, 'command_config'] = command_config

        if origin_config.strip():
            source_config_json, tasks = parse_config_file(config_str=command_config,
                                                          config_model=config_models['conbined_Juniper'], subdivide_model=config_models['Juniper'])

            for future, template in tasks:  # 处理LLM解析的任务
                result = future.result()

                template.update(result)

            trans_res_dict = config_translater.translation(source_config_json, source_vendor, 'HUAWEI',
                                                           source_total_config=command_config, add_parents=False)
            df.at[index, 'config_json'] = json.dumps(source_config_json, ensure_ascii=False, indent=4)
            df.at[index, 'translated'] = trans_res_dict['trans_res']
            print(trans_res_dict['trans_res'])
        else:
            df.at[index, 'config_json'] = ''
            df.at[index, 'translated'] = ''


    df.to_excel('Juniper_translated.xlsx', index=False)
