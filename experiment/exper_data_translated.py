# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：exper_data_translated.py
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_community.embeddings import HuggingFaceEmbeddings
from src.F_device_configtrans import Config_Translater, Translation_Model, mapping_library_load, config_matchers_load, \
    process_juniper_json
import os
import json
from tqdm import tqdm  # 用于显示进度条


def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def batch_translate(config_translater, input_dir, output_dir, source_vendor, target_vendor, batch_size=100):
    """
    批量翻译配置文件
    :param config_translater: 配置翻译器实例
    :param input_dir: 输入目录
    :param output_dir: 输出目录
    :param source_vendor: 源供应商
    :param target_vendors: 目标供应商列表
    """
    # 获取所有配置文件
    config_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]

    # 创建输出目录
    os.makedirs(os.path.join(output_dir, target_vendor), exist_ok=True)

    # 遍历每个文件进行翻译
    successed_files = 0
    with ThreadPoolExecutor(max_workers=10) as executor:  # 多线程好像有点问题，暂时不使用
        futures = []
        for file_index in range(batch_size):
            config_file = config_files.pop(0)
            futures.append(executor.submit(translate_single_file,
                                           config_translater, input_dir, output_dir,
                                           source_vendor, target_vendor, config_file))
        with tqdm(total=batch_size, desc="Successed files") as pbar:
            i = 0
            while i < len(futures):
                future = futures[i]
                try:
                    if future.result():
                        successed_files += 1
                        pbar.update(1)
                except Exception as e:
                    print(f"\nError: {str(e)}")
                    if config_files:
                        config_file = config_files.pop(0)
                        futures.append(executor.submit(translate_single_file,
                                                       config_translater, input_dir, output_dir,
                                                       source_vendor, target_vendor, config_file))
                i += 1

        print(f"Translated {successed_files} configs")
    print(f"Translated {successed_files} configs")


def translate_single_file(config_translater, input_dir, output_dir,
                          source_vendor, target_vendor, config_file):
    # 加载配置
    config_path = os.path.join(input_dir, config_file)
    json_config = load_json_file(config_path)
    if source_vendor == 'Juniper':
        json_config = process_juniper_json(json_config)
    file_name = os.path.splitext(config_file)[0]

    # 翻译到目标供应商
    output_path = os.path.join(output_dir, target_vendor, f"{file_name}.txt")
    trans_res, _ = config_translater.translation(json_config, source_vendor, target_vendor)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(trans_res)
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
    output_dir = './exper_data/translated_config'

    vendors = ["Cisco", "HUAWEI", "Juniper"]
    config_num = [100, 500, 1000, 2000]
    # config_num = [2000]
    local_EMmodel_path = '../EmbeddingModel/MiniLM-L6-v2'
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": device})

    for scale in config_num:
        for source_vendor in vendors:
            for target_vendor in vendors:
                if source_vendor == target_vendor:
                    continue
                if (not source_vendor == 'Juniper') and (not target_vendor == 'Juniper'): # 只翻译Juniper到其他供应商
                # if (source_vendor == 'Juniper') or (target_vendor == 'Juniper'): # 不考虑juniper
                    continue
                source_config_dir = f'./exper_data/{source_vendor}'
                output_save_dir = os.path.join(output_dir, str(scale), source_vendor)  # 当前处理的是哪个scale的哪个源供应商
                os.makedirs(output_save_dir, exist_ok=True)
                delete_outdate_files(os.path.join(output_dir, str(scale), source_vendor, target_vendor))

                print(f"exper for {scale}, {source_vendor} to {target_vendor} translation")
                mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/different_scale/{{}}_{{}}_{scale}.json'
                templates_path = f'../dataset_multi_vendor_config/config_command_node/different_scale/{{}}_{scale}.json'
                config_model_dir = f'../dataset_multi_vendor_config/config_model/different_scale/{{}}_{scale}.json'

                mapping_libraries = mapping_library_load(mapping_library_path, vendors)
                config_matchers = config_matchers_load(templates_path, vendors)

                translation_llm = Translation_Model('deepseek-chat', config_model_dir=config_model_dir, vendors=vendors)

                config_translater = Config_Translater(mapping_libraries, config_matchers,
                                                      translation_llm, embedding_model)
                # 执行批量翻译
                batch_translate(config_translater, source_config_dir, output_save_dir,
                                source_vendor=source_vendor,
                                target_vendor=target_vendor,
                                batch_size=100)

if __name__ == "__main__":
    main()
