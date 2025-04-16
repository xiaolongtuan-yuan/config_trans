# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：exper_data_translated.py
"""
import ast
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_community.embeddings import HuggingFaceEmbeddings

from experiment.tree_match import grammatical_match
from src.F_device_configtrans import Config_Translater, Translation_Model, mapping_library_load, config_matchers_load, \
    process_juniper_json
import os
import json
from tqdm import tqdm  # 用于显示进度条


def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def batch_translate(config_translater, input_dir, output_dir, source_vendor, target_vendor, batch_size=None):
    config_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    os.makedirs(os.path.join(output_dir, target_vendor), exist_ok=True)

    successed_files = 0
    error_mapping_rules = defaultdict(set)
    error_mapping_rules_freq = defaultdict(int)

    if batch_size is None:
        batch_size = len(config_files)
    with ThreadPoolExecutor(max_workers=1) as executor:  # 多线程好像有点问题，暂时不使用
        futures = []
        for file_index in range(batch_size):
            config_file = config_files.pop(0)
            futures.append(executor.submit(translate_single_file,
                                           config_translater, input_dir,error_mapping_rules,error_mapping_rules_freq,
                                           source_vendor, target_vendor, config_file))
        with tqdm(total=batch_size, desc="Successed files") as pbar:
            i = 0
            while i < len(futures):
                future = futures[i]
                if future.result():
                    successed_files += 1
                    pbar.update(1)
                i += 1

        print(f"Translated {successed_files} configs")
    total_usage = sum(error_mapping_rules_freq.values())
    error_mapping_rules_freq = {k: round(v / total_usage, 4) for k, v in
                     sorted(error_mapping_rules_freq.items(), key=lambda item: item[1], reverse=True)}
    error_mapping_rules_freq = {str([source_temp, error_matchs]): error_mapping_rules_freq[source_temp] for source_temp, error_matchs in error_mapping_rules.items()}
    error_mapping_rules_freq = sorted(error_mapping_rules_freq.items(), key=lambda item: item[1], reverse=True)
    return error_mapping_rules_freq



def translate_single_file(config_translater, input_dir, error_mapping_rules, error_mapping_rules_freq,
                          source_vendor, target_vendor, config_file):
    # 加载配置
    config_path = os.path.join(input_dir, config_file)
    json_config = load_json_file(config_path)
    if source_vendor == 'Juniper':
        json_config = process_juniper_json(json_config)
    device_name = os.path.splitext(config_file)[0]

    _, map_rule_data = config_translater.translation_without_llm(json_config, source_vendor, target_vendor,
                                                                 istatistics=True)
    config_model = config_translater.translation_llm.config_models[target_vendor]
    real_dir = f'./exper_data/lable/{target_vendor}'
    error_mapping_data, error_mapping_rules_count = grammatical_match(device_name, map_rule_data, real_dir, config_model)
    for source_temp, error_matchs in error_mapping_data.items():
        error_mapping_rules[source_temp].update(error_matchs)
    for source_temp, error_count in error_mapping_rules_count.items():
        error_mapping_rules_freq[source_temp] += error_count

    return True


def delete_outdate_files(file_dir):
    os.makedirs(file_dir, exist_ok=True)
    # 清空目录下的所有文件
    for file in os.listdir(file_dir):
        file_path = os.path.join(file_dir, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")


def main():
    # 初始化路径
    device = "cuda:0"
    output_dir = './exper_data/translated_config_without_llm'

    vendors = ["Cisco", "HUAWEI", "Juniper"]
    local_EMmodel_path = '../EmbeddingModel/MiniLM-L6-v2'
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": device})
    scales = [2000]
    for scale in scales:
        for source_vendor in vendors:
            for target_vendor in vendors:
                if source_vendor == target_vendor:
                    continue
                source_config_dir = f'./exper_data/{source_vendor}'
                output_save_dir = os.path.join(output_dir, str(scale), source_vendor)  # 当前处理的是哪个scale的哪个源供应商
                os.makedirs(output_save_dir, exist_ok=True)
                delete_outdate_files(os.path.join(output_dir, str(scale), source_vendor, target_vendor))

                print(f"exper for {scale}, {source_vendor} to {target_vendor} translation without llm")
                mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/different_scale/{{}}_{{}}_{scale}.json'
                templates_path = f'../dataset_multi_vendor_config/config_command_node/different_scale/{{}}_{scale}.json'
                config_model_dir = f'../dataset_multi_vendor_config/config_model/different_scale/{{}}_{scale}.json'

                mapping_libraries = mapping_library_load(mapping_library_path, vendors)
                config_matchers = config_matchers_load(templates_path, vendors, semantic_topk=3)

                translation_llm = Translation_Model('deepseek-chat', config_model_dir=config_model_dir, vendors=vendors)

                config_translater = Config_Translater(mapping_libraries, config_matchers,
                                                      translation_llm, embedding_model)
                # 执行批量翻译
                error_mapping_rules_freq = batch_translate(config_translater, source_config_dir, output_save_dir,
                                source_vendor=source_vendor,
                                target_vendor=target_vendor)

                with open(f'./exper_res/error_mapping_rules_freq/{source_vendor}_{target_vendor}_error_mapping_rules_freq.json', 'w', encoding='utf-8') as f:
                    json.dump(error_mapping_rules_freq, f, ensure_ascii=False, indent=4)
                print(f"finished {source_vendor} to {target_vendor} translation without llm")

if __name__ == "__main__":
    main()
