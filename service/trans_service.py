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
from src.F_new_device_configtrans import mapping_library_load, config_matchers_load, Translation_Model, \
    Config_Translater, config_model_load

project_root = Path(__file__).parent.parent
device = "cuda:0"


def initialize_translation_service():
    vendors = ["Cisco", "HUAWEI", "Juniper"]
    templates_path = f'../dataset_multi_vendor_config/config_command_node/verified_data/{{}}.json'
    config_model_dir = f'../dataset_multi_vendor_config/config_model/verified_data/{{}}.json'
    manual_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/manual_mapping/{{}}_{{}}.json'
    error_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/error_mapping/{{}}_{{}}.json'
    module_match_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}_module_match.json'
    mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}.json'

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
    return config_translater


config_translater = initialize_translation_service()


def translate_config(json_config, vendor, target_vendor, config):
    # 执行翻译
    trans_res_dict = config_translater.translation(json_config, vendor, target_vendor, tau=0.999, source_total_config=config)
    return trans_res_dict['trans_res'], trans_res_dict['map_rule_freq']


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
