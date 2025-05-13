# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：exper_data_translated.py
"""
import sys

sys.path.append("/data/public/hrx/Repositories/config_trans")
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_community.embeddings import HuggingFaceEmbeddings

from experiment.tree_match import parse_config_file_intact, parse_config_file_content_intact, calculate_match_ratio, \
    get_all_templates
from src.F_new_device_configtrans import Config_Translater, Translation_Model, mapping_library_load, \
    config_matchers_load, config_model_load
import os
import json
from tqdm import tqdm
from pathlib import Path


def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def batch_translate(config_translater, input_dir, output_dir, real_config_dir, real_command_tree_dir, source_vendor,
                    target_vendor, batch_size=None, tau=None):
    config_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    os.makedirs(os.path.join(output_dir, target_vendor), exist_ok=True)

    successed_files = 0
    if batch_size is None:
        batch_size = len(config_files)
    with ThreadPoolExecutor(max_workers=5) as executor:  # 多线程好像有点问题，暂时不使用
        futures = []
        for file_index in range(batch_size):
            config_file = config_files.pop(0)
            futures.append(executor.submit(translate_single_file,
                                           config_translater, input_dir, output_dir, real_config_dir,
                                           real_command_tree_dir,
                                           source_vendor, target_vendor, config_file))
        with tqdm(total=batch_size, desc="Successed files") as pbar:
            i = 0
            while i < len(futures):
                future = futures[i]
                # try:
                #     if future.result():
                #         successed_files += 1
                #         pbar.update(1)
                # except Exception as e:
                #     print(f"\nError: {str(e)}")
                #     if config_files:
                #         config_file = config_files.pop(0)
                #         futures.append(executor.submit(translate_single_file,
                #                                        config_translater, input_dir, output_dir, real_config_dir,real_command_tree_dir,
                #                                        source_vendor, target_vendor, config_file))

                if future.result():
                    successed_files += 1
                    pbar.update(1)
                i += 1

        print(f"Translated {successed_files} configs")
    print(f"Translated {successed_files} configs")


def translate_single_file(config_translater, input_dir, output_dir, real_config_dir, real_command_tree_dir,
                          source_vendor, target_vendor, config_file):
    # 加载配置
    config_path = os.path.join(input_dir, config_file)
    json_config = load_json_file(config_path)
    txt_config_path = config_path.replace('command_tree', 'text_config')
    txt_config_path = txt_config_path.replace('.json', '.txt')
    file_name = os.path.splitext(config_file)[0]
    with open(txt_config_path, 'r', encoding='utf-8') as f:
        source_total_config = f.read()

    trans_res, trans_mapping_info, trans_templates, map_rule_freq = config_translater.translation(json_config,
                                                   source_vendor,
                                                   target_vendor,
                                                   tau=0.001,
                                                   source_total_config=source_total_config)

    # 评估
    evaluate_res = {
        "command_accuracy": 0,
        "missed_commands": [],
        "grammatical_accuracy": 0,
        "missed_templates": []
    }
    real_command_tree_path = os.path.join(real_command_tree_dir, f"{file_name}.json")
    real_config_path = os.path.join(real_config_dir, f"{file_name}.txt")

    with open(real_command_tree_path, encoding='utf-8') as f:
        real_command_tree = json.load(f)
    with open(real_config_path, encoding='utf-8') as f:
        real_config = f.read()

    expected_commands = parse_config_file_content_intact(real_config)
    result_commands = parse_config_file_content_intact(trans_res)

    command_match_score, command_match_account, missed_commands = calculate_match_ratio(result_commands,
                                                                                        expected_commands,
                                                                                        [],
                                                                                        [])
    evaluate_res['command_accuracy'] = command_match_score / command_match_account
    evaluate_res['missed_commands'] = missed_commands

    expected_templates = get_all_templates(real_command_tree)

    # print(f"expected_templates: {expected_templates}")
    # print(f"trans_templates: {trans_templates}")

    match_score, match_account, error_templates = calculate_match_ratio(trans_templates,
                                                                        expected_templates,
                                                                        [],
                                                                        [])
    evaluate_res['missed_templates'] = error_templates
    evaluate_res['grammatical_accuracy'] = match_score / match_account

    tran_res_output_path = os.path.join(output_dir, target_vendor, f"{file_name}.txt")
    tran_temp_output_path = os.path.join(output_dir, target_vendor, f"{file_name}_temp.json")
    label_config_text_path = os.path.join(output_dir, target_vendor, f"{file_name}_label_text.txt")
    label_command_tree_path = os.path.join(output_dir, target_vendor, f"{file_name}_label_command_tree.json")
    tran_map_rule_usage_output_path = os.path.join(output_dir, target_vendor, f"{file_name}_map_rules.json")
    tran_evaluate_output_path = os.path.join(output_dir, target_vendor, f"{file_name}_evaluate.json")

    with open(tran_res_output_path, 'w', encoding='utf-8') as f:
        f.write(trans_res)
    with open(tran_temp_output_path, 'w', encoding='utf-8') as f:
        json.dump(trans_templates, f, ensure_ascii=False, indent=4)
    with open(label_config_text_path, mode='w', encoding='utf-8') as f:
        f.write(real_config)
    with open(label_command_tree_path, mode='w', encoding='utf-8') as f:
        json.dump(real_command_tree, f, ensure_ascii=False, indent=4)
    with open(tran_map_rule_usage_output_path, 'w', encoding='utf-8') as f:
        json.dump(map_rule_freq, f, ensure_ascii=False, indent=4)
    with open(tran_evaluate_output_path, 'w', encoding='utf-8') as f:
        json.dump(evaluate_res, f, ensure_ascii=False, indent=4)
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
    name = 'topk'
    data_dir = 'valid_data'
    output_dir = f'../experiment/exper_data/translated_config_with_{name}'
    manual_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/manual_mapping/{{}}_{{}}.json'
    templates_path = f'../dataset_multi_vendor_config/config_command_node/verified_data/{{}}.json'
    error_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/error_mapping/{{}}_{{}}.json'

    vendors = ["Cisco", "HUAWEI", "Juniper"]
    topk_values = [1,2,3,4]
    local_EMmodel_path = '../EmbeddingModel/MiniLM-L6-v2'
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": device})

    for topk in topk_values:
        mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}.json'
        module_match_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}_module_match.json'
        config_model_dir = f'../dataset_multi_vendor_config/config_model/verified_data/{{}}.json'

        for source_vendor in vendors:
            for target_vendor in vendors:
                if source_vendor == target_vendor:
                    continue
                source_config_dir = f'../experiment/test_dataset/{data_dir}/command_tree/{source_vendor}' if source_vendor != 'Juniper' else f'../experiment/test_dataset/{data_dir}/command_tree/Juniper_subdivided'
                real_config_dir = f'../experiment/test_dataset/{data_dir}/text_config/{target_vendor}'
                real_command_tree_dir = f'../experiment/test_dataset/{data_dir}/command_tree/{target_vendor}'

                output_save_dir = os.path.join(output_dir, str(topk), source_vendor)
                os.makedirs(output_save_dir, exist_ok=True)

                print(f"exper for {topk}, {source_vendor} to {target_vendor} translation without llm")

                mapping_libraries = mapping_library_load(mapping_library_path, vendors, manual_mapping_path,
                                                         error_mapping_path)

                config_matchers = config_matchers_load(templates_path, config_model_dir, module_match_path, vendors, topk=topk)

                config_models = config_model_load(config_model_dir, vendors)

                translation_llm = Translation_Model('aliyun_deepseek-v3', config_model_dir=config_model_dir,
                                                    vendors=vendors,
                                                    endpoint_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

                config_translater = Config_Translater(mapping_libraries, config_matchers,
                                                      translation_llm, embedding_model, config_models)
                # 执行批量翻译
                batch_translate(config_translater, source_config_dir, output_save_dir, real_config_dir,
                                real_command_tree_dir,
                                source_vendor=source_vendor,
                                target_vendor=target_vendor)


if __name__ == "__main__":
    main()
