# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/21 19:54
@Auth ： xiaolongtuan
@File ：trans_service.py
"""
import json
import re
from pathlib import Path
from langchain_community.embeddings import HuggingFaceEmbeddings

from data_process.rearrange_command_tree import parse_config, merge_tree_with_flat, LLM_Model
from data_process.subdivision_juniper_json import split_parameters
from src.A_LLM_Parse_Config import load_client, process_file_service
from src.F_new_device_configtrans import mapping_library_load, config_matchers_load, Translation_Model, \
    Config_Translater, config_model_load

project_root = Path(__file__).parent.parent
device = "cuda:0"

def find_juniper_template(command, config_model, subdivide_model):
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

def find_simple_template(command, config_model):
    for template, details in config_model.items():
        if isinstance(details, dict) and 'template' in details:
            sub_template = find_simple_template(command, details)
            if sub_template:
                return sub_template

            pattern = re.sub(r"\[[^\]]+\]", r'(\\S+)', details['template'])
            pattern = f'^{pattern}$'
            try:
                if re.match(pattern, command):
                    return {
                        "template": details['template'],
                        "command": command,
                        "explanation": details['explanation'],
                        "parameters": details['parameters'],
                    }
                else:
                    continue
            except re.error:
                continue
    return None

def parse_config_file(config_str, vendor):
    llm_model = LLM_Model('deepseek-chat')
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

        if vendor == 'Juniper':
            config_model = config_models['Juniper']
            subdivide_model = config_models['Juniper']
            template = find_juniper_template(content, config_model, subdivide_model)
        else:
            config_model = config_models[vendor]
            template = find_simple_template(content, config_model)

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

def initialize_translation_service():
    # vendors = ["Cisco", "HUAWEI", "Juniper"]
    # templates_path = f'../dataset_multi_vendor_config/config_command_node/verified_data/{{}}.json'
    # config_model_dir = f'../dataset_multi_vendor_config/config_model/verified_data/{{}}.json'
    # manual_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/manual_mapping/{{}}_{{}}.json'
    # error_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/error_mapping/{{}}_{{}}.json'
    # module_match_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}_module_match.json'
    # mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}.json'
    vendors = ["Cisco", "HUAWEI", "Juniper"]
    templates_path = f'../dataset_multi_vendor_config/config_command_node/all_data/{{}}.json'
    config_model_dir = f'../dataset_multi_vendor_config/config_model/all_data/{{}}.json'
    manual_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/manual_mapping/{{}}_{{}}.json'
    error_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/error_mapping/{{}}_{{}}.json'
    module_match_path = f'../dataset_multi_vendor_config/mapping_template_library/all_data/{{}}_{{}}_module_match.json'
    mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/all_data/{{}}_{{}}.json'


    # 加载规则映射库
    print('Mapping library loading.')
    mapping_libraries = mapping_library_load(mapping_library_path, vendors, manual_mapping_path,
                                             error_mapping_path)
    # 加载配置匹配器
    print('Config matchers loading.')
    config_matchers = config_matchers_load(templates_path, config_model_dir, module_match_path, vendors)

    # 加载配置模型
    print('Config models loading.')
    config_models = config_model_load(config_model_dir, vendors)

    # 文本嵌入模型加载
    print('Embedding model loading.')
    local_EMmodel_path = str(project_root / 'EmbeddingModel/MiniLM-L6-v2')
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": device})

    # 加载用于配置翻译的语言模型
    print('Translation model based on llm loading.')
    translation_llm = Translation_Model('aliyun_deepseek-v3', config_model_dir=config_model_dir,
                                        vendors=vendors,
                                        endpoint_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    # 创建翻译器
    print('Config translater loading.')
    config_translater = Config_Translater(mapping_libraries, config_matchers,
                                          translation_llm, embedding_model, config_models)
    return config_translater, config_models


config_translater, config_models = initialize_translation_service()


def translate_config(json_config, vendor, target_vendor, config):
    # 执行翻译
    trans_res_dict = config_translater.translation(json_config, vendor, target_vendor, tau=0.999, source_total_config=config)
    return trans_res_dict['trans_res'], trans_res_dict['trans_mapping_info']


def config_parse(config, vendor):
    model_name = "deepseek-chat"
    client = load_client(model_name, endpoint_url='https://api.deepseek.com/v1')
    config_str = process_file_service(config, vendor, client, model_name)
    config = json.loads(config_str)
    return config

def parse_json_2_visible_txt(data, indent=0):
    result = ""
    for key, value in data.items():
        if isinstance(value, dict):
            result += "  " * indent + f"- {key}:\n"
            if 'template' in value:
                result += "  " * (indent + 1) + f"- {value['template']}\n"
            if 'explanation' in value:
                result += "  " * (indent + 1) + f"- {value['explanation']}\n"
            result += parse_json_2_visible_txt(value, indent + 2)
    return result


if __name__ == '__main__':
    vendor="Cisco"
    target_vendor="HUAWEI"
    config='''
router ospf 2
  router-id 10.1.3.10
  network 10.1.3.0 0.0.0.255 area 0.0.0.1
'''
#     config='''
# interface GigabitEthernet1/0/0
#  ip address 10.1.1.10 255.255.255.0
# !
# interface Loopback0
#  ip address 192.168.0.1 255.255.255.255
# '''
    source_config_json, tasks=parse_config_file(config, vendor)
    for future, template in tasks:  # 处理LLM解析的任务
        result = future.result()
        template.update(result)

    translation_result, trans_mapping_info = translate_config(source_config_json, vendor, target_vendor, config)

    print(translation_result)
