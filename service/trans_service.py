# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/21 19:54
@Auth ： xiaolongtuan
@File ：trans_service.py
"""
import json
from pathlib import Path
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.A_LLM_Parse_Config import load_client, process_file_service
from src.F_device_configtrans import mapping_library_load, config_matchers_load, translation_model, Config_Translater

project_root = Path(__file__).parent.parent
device = "cuda:0"
def initialize_translation_service():
    vendors = ["Cisco", "HUAWEI", "Juniper"]
    mapping_library_path = str(project_root / 'dataset_multi_vendor_config/mapping_template_library/{}_{}.json')
    templates_path = str(project_root / 'dataset_multi_vendor_config/config_command_node/{}.json')

    # 加载规则映射库
    print('Mapping library loading.')
    mapping_libraries = mapping_library_load(mapping_library_path, vendors)
    # 加载配置匹配器
    print('Config matchers loading.')
    config_matchers = config_matchers_load(templates_path, vendors)
    # 文本嵌入模型加载
    print('Embedding model loading.')
    local_EMmodel_path = str(project_root / 'EmbeddingModel/MiniLM-L6-v2')
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": device})

    # 加载用于配置翻译的语言模型
    print('Translation model based on llm loading.')
    translation_llm = translation_model('deepseek-chat')

    # 创建翻译器
    print('Config translater loading.')
    config_translater = Config_Translater(mapping_libraries, config_matchers,
                                          translation_llm, embedding_model)
    return config_translater

config_translater = initialize_translation_service()

def translate_config(json_config, vendor, target_vendor):
    # 执行翻译
    translation_result, trans_mapping_info = config_translater.translation(json_config, vendor, target_vendor)
    return translation_result, trans_mapping_info

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
