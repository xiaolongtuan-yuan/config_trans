# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：exper_data_translated.py
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_community.embeddings import HuggingFaceEmbeddings
from src.F_new_device_configtrans import Config_Translater, Translation_Model, mapping_library_load, config_matchers_load, \
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
    statistic_res = {
        "command_count": 0,
        "rule_ccount": 0,
        "llm_ccount": 0,
    }
    map_rule_freq = {}
    if batch_size is None:
        batch_size = len(config_files)
    with ThreadPoolExecutor(max_workers=1) as executor:  # 多线程好像有点问题，暂时不使用
        futures = []
        for file_index in range(batch_size):
            config_file = config_files.pop(0)
            futures.append(executor.submit(translate_single_file,
                                           config_translater, input_dir, statistic_res, map_rule_freq,
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
    print(statistic_res)
    total_usage = sum(map_rule_freq.values())
    map_rule_freq = {k: round(v / total_usage, 4) for k, v in
                     sorted(map_rule_freq.items(), key=lambda item: item[1], reverse=True)}
    return statistic_res, map_rule_freq



def translate_single_file(config_translater, input_dir, statistic_res, map_rule_freq,
                          source_vendor, target_vendor, config_file):
    # 加载配置
    config_path = os.path.join(input_dir, config_file)
    json_config = load_json_file(config_path)
    file_name = os.path.splitext(config_file)[0]

    statistic_data, map_rule_data = config_translater.translation_without_llm(json_config, source_vendor, target_vendor,
                                                                 istatistics=True)
    statistic_res['command_count'] += statistic_data['command_count']
    statistic_res['rule_ccount'] += statistic_data['rule_ccount']
    statistic_res['llm_ccount'] += statistic_data['llm_ccount']
    for rule, use_count in map_rule_data.items():
        if rule in map_rule_freq:
            map_rule_freq[rule] += use_count
        else:
            map_rule_freq[rule] = use_count

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
    scales = [177]
    scales_covers_res = {}
    for scale in scales:
        # mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/different_scale/{{}}_{{}}_{scale}.json'
        # templates_path = f'../dataset_multi_vendor_config/config_command_node/different_scale/{{}}_{scale}.json'
        # config_model_dir = f'../dataset_multi_vendor_config/config_model/different_scale/{{}}_{scale}.json'
        # module_match_path = f'../dataset_multi_vendor_config/mapping_template_library/different_scale/{{}}_{{}}_{scale}_module_match.json'
        # manual_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/manual_mapping/{{}}_{{}}.json'
        # error_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/error_mapping/{{}}_{{}}.json'
        mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}.json'
        manual_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/manual_mapping/{{}}_{{}}.json'
        error_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/error_mapping/{{}}_{{}}.json'
        module_match_path = f'../dataset_multi_vendor_config/mapping_template_library/multi_module/{{}}_{{}}_module_match.json'
        templates_path = f'../dataset_multi_vendor_config/config_command_node/verified_data/{{}}.json'
        config_model_dir = f'../dataset_multi_vendor_config/config_model/verified_data/{{}}.json'


        statistic_res = {
            "command_count": 0,
            "rule_ccount": 0,
            "llm_ccount": 0,
        }
        for source_vendor in vendors:
            for target_vendor in vendors:
                if source_vendor == target_vendor:
                    continue
                source_config_dir = f'../experiment/test_dataset/valid_data/command_tree/{source_vendor}' if source_vendor != 'Juniper' else f'../experiment/test_dataset/valid_data/command_tree/Juniper_subdivided'

                output_save_dir = os.path.join(output_dir, str(scale), source_vendor)  # 当前处理的是哪个scale的哪个源供应商
                os.makedirs(output_save_dir, exist_ok=True)
                delete_outdate_files(os.path.join(output_dir, str(scale), source_vendor, target_vendor))

                print(f"exper for {scale}, {source_vendor} to {target_vendor} translation without llm")

                mapping_libraries = mapping_library_load(mapping_library_path, vendors, manual_mapping_path, error_mapping_path)
                config_matchers = config_matchers_load(templates_path, config_model_dir, module_match_path, vendors, topk=3)

                translation_llm = Translation_Model('deepseek-chat', config_model_dir=config_model_dir, vendors=vendors)

                config_translater = Config_Translater(mapping_libraries, config_matchers,
                                                      translation_llm, embedding_model)
                # 执行批量翻译
                cover_data, map_rule_freq = batch_translate(config_translater, source_config_dir, output_save_dir,
                                source_vendor=source_vendor,
                                target_vendor=target_vendor)

                with open(f'./exper_res/{source_vendor}_{target_vendor}_map_rule_freq.json', 'w', encoding='utf-8') as f:
                    json.dump(map_rule_freq, f, ensure_ascii=False, indent=4)
                statistic_res['command_count'] += cover_data['command_count']
                statistic_res['rule_ccount'] += cover_data['rule_ccount']
                statistic_res['llm_ccount'] += cover_data['llm_ccount']
        statistic_res['rule_cover_rate'] = statistic_res['rule_ccount'] / statistic_res['command_count']
        statistic_res['llm_cover_rate'] = statistic_res['llm_ccount'] / statistic_res['command_count']
        scales_covers_res[scale] = statistic_res
        print(statistic_res)
    with open('./exper_res/cover_statistic.json', 'w', encoding='utf-8') as f:
        json.dump(scales_covers_res, f, ensure_ascii=False, indent=4)



if __name__ == "__main__":
    main()
