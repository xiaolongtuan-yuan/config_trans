# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：exper_data_translated.py
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_community.embeddings import HuggingFaceEmbeddings
from src.F_device_configtrans import Config_Translater, Translation_Model, mapping_library_load, config_matchers_load
import os
import json
from tqdm import tqdm  # 用于显示进度条

def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def batch_translate(config_translater, input_dir, output_dir, source_vendor, target_vendors):
    """
    批量翻译配置文件
    :param config_translater: 配置翻译器实例
    :param input_dir: 输入目录
    :param output_dir: 输出目录
    :param source_vendor: 源供应商
    :param target_vendors: 目标供应商列表
    """
    # 获取所有配置文件
    config_files = [f for f in os.listdir(input_dir) if f.endswith('.json')][:200]

    # 创建输出目录
    for vendor in target_vendors:
        os.makedirs(os.path.join(output_dir, vendor), exist_ok=True)

    # 遍历每个文件进行翻译
    successed_files = 0
    # with ThreadPoolExecutor() as executor: # 多线程好像有点问题，暂时不使用
    #     futures = []
    #     for config_file in config_files:
    #         futures.append(executor.submit(translate_single_file,
    #                                        config_translater, input_dir, output_dir,
    #                                        source_vendor, target_vendors, config_file))
    #     for future in tqdm(as_completed(futures), total=len(futures), desc="Translating configs"):
    #         try:
    #             if future.result():
    #                 successed_files += 1
    #         except Exception as e:
    #             print(f"\nError: {str(e)}")
    #     print(f"Translated {successed_files} configs")
    for config_file in tqdm(config_files, desc="Translating configs"):
        try:
            if translate_single_file(config_translater, input_dir, output_dir,
                                     source_vendor, target_vendors, config_file):
                successed_files += 1
        except Exception as e:
            print(f"\nError: {str(e)}")
    print(f"Translated {successed_files} configs")

def translate_single_file(config_translater, input_dir, output_dir,
                         source_vendor, target_vendors, config_file):
    try:
        # 加载配置
        config_path = os.path.join(input_dir, config_file)
        json_config = load_json_file(config_path)
        file_name = os.path.splitext(config_file)[0]

        # 翻译到每个目标供应商
        for target_vendor in target_vendors:
            output_path = os.path.join(output_dir, target_vendor, f"{file_name}.txt")
            trans_res, _ = config_translater.translation(json_config, source_vendor, target_vendor)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(trans_res)
        return True
    except Exception as e:
        print(f"\nError translating {config_file}: {str(e)}")
        # 删除在os.path.join(output_dir, "Cisco", f"{file_name}.json")的文件
        os.remove(os.path.join(input_dir, config_file))
        return False


def main():
    # 初始化路径
    device = "cuda:0"
    cisco_config_dir = './exper_data/Cisco'
    output_dir = './exper_data/cisco_translated_config_with_mapping_examined'


    vendors = ["Cisco", "HUAWEI", "Juniper"]
    for target_vendor in ['HUAWEI', 'Juniper']:
        output_path = os.path.join(output_dir, target_vendor)
        os.makedirs(output_path, exist_ok=True)


    mapping_library_path = '../dataset_multi_vendor_config/mapping_template_library_examined/{}_{}.json'
    templates_path = '../dataset_multi_vendor_config/config_command_node/{}.json'

    print('Mapping library loading.')
    mapping_libraries = mapping_library_load(mapping_library_path, vendors)
    print('Config matchers loading.')
    config_matchers = config_matchers_load(templates_path, vendors)
    print('Embedding model loading.')
    local_EMmodel_path = '../EmbeddingModel/MiniLM-L6-v2'
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": device})
    print('Translation model based on llm loading.')
    translation_llm = Translation_Model('deepseek-chat')

    HUAWEI_config_translater = Config_Translater(mapping_libraries, config_matchers,
                                          translation_llm, embedding_model)
    # 执行批量翻译
    batch_translate(HUAWEI_config_translater, cisco_config_dir, output_dir,
                    source_vendor='Cisco',
                    target_vendors=['HUAWEI'])

    # Juniper_config_translater = Config_Translater(mapping_libraries, config_matchers,
    #                                       translation_llm, embedding_model)
    # # 执行批量翻译
    # batch_translate(Juniper_config_translater, cisco_config_dir, output_dir,
    #                 source_vendor='Cisco',
    #                 target_vendors=['Juniper'])


if __name__ == "__main__":
    main()
