# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：exper_data_translated.py
"""
import re
import sys
from copy import deepcopy

from numpy.lib.utils import source

sys.path.append("/data/public/hrx/Repositories/config_trans")
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_community.embeddings import HuggingFaceEmbeddings

from experiment.tree_match import parse_config_file_content_intact, calculate_match_ratio, \
    get_all_templates, command_template_process
from src.F_device_configtrans2 import Config_Translater, Translation_Model, mapping_library_load, \
    config_matchers_load, config_model_load, ConfigNode
import os
import json
from tqdm import tqdm


def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


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
                    return details
                else:
                    continue
            except re.error:
                continue
    return None


def unify_template(unified_json, config_model):
    for command, details in unified_json.items():
        if isinstance(details, dict) and 'template' in details:
            unified_template = find_simple_template(command, config_model)
            if unified_template:
                details['template'] = unified_template['template']
                unify_template(details, unified_template)
            else:
                continue


def batch_translate(config_translater, input_dir, output_dir, real_config_dir, real_command_tree_dir, source_vendor,
                    target_vendor, batch_size=None):
    config_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    os.makedirs(os.path.join(output_dir, target_vendor), exist_ok=True)

    successed_files = 0
    if batch_size is None:
        batch_size = len(config_files)
    with ThreadPoolExecutor(max_workers=10) as executor:  # 多线程好像有点问题，暂时不使用
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

                try:
                    if future.result():
                        successed_files += 1
                except Exception as e:
                    print(e)
                finally:
                    pbar.update(1)
                    i += 1

        print(f"Translated {successed_files} configs")
    print(f"Translated {successed_files} configs")


def merge_simple_config(real_config):
    node_id = 0
    lines = real_config.split('\n')
    if not lines:
        return {}
    root = ConfigNode('system', "", node_id)
    node_id += 1

    stack = [(root, -1)]  # (缩进级别, 当前字典)
    for line in lines:
        if not line.strip() or line.strip().startswith(('#', '!', '*', '/*', '*/', '/')):
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        while stack and stack[-1][1] >= indent:
            stack.pop()
        node = ConfigNode(content, '', node_id, '')
        node_id += 1

        stack[-1][0].add_child(node)
        stack.append((node, indent))

    root.merge_child()
    merged_config = "\n".join(root.to_lines()[1:])
    return merged_config


def translate_single_file(config_translater, input_dir, output_dir, real_config_dir, real_command_tree_dir,
                          source_vendor, target_vendor, config_file):
    # 加载配置
    config_path = os.path.join(input_dir, config_file)
    json_config = load_json_file(config_path)
    # 需要根据configmodel修改一下template
    unified_json_config = deepcopy(json_config)
    unify_template(unified_json_config, config_translater.config_models[source_vendor])

    txt_config_path = config_path.replace('command_tree', 'text_config')
    txt_config_path = txt_config_path.replace('.json', '.txt')
    if 'Juniper_subdivided' in txt_config_path:
        txt_config_path = txt_config_path.replace('Juniper_subdivided', 'Juniper')
    with open(txt_config_path, 'r', encoding='utf-8') as f:
        source_total_config = f.read()

    file_name = os.path.splitext(config_file)[0]
    tran_res_output_path = os.path.join(output_dir, target_vendor, f"{file_name}.txt")

    trans_res_dict = config_translater.translation(unified_json_config,
                                                   source_vendor,
                                                   target_vendor,
                                                   tau=0.999,
                                                   source_total_config=source_total_config)
    # 评估
    evaluate_res = {
        "command_accuracy": 0,
        "missed_commands": [],
        "grammatical_accuracy": 0,
        "missed_templates": [],
        "llm_command_accuracy": {},
        'llm_command_ratio': 0,
        'heuristic_command_ratio': 0,
        "command_for_llm": trans_res_dict['command_for_llm'],
        "command_for_llm_rate": len(trans_res_dict['command_for_llm']) / len(trans_res_dict['source_commands']),
        "command_for_heuristic": trans_res_dict['command_for_heuristic'],
        "command_for_heuristic_rate": len(trans_res_dict['command_for_heuristic']) / len(
            trans_res_dict['source_commands']),
        "llm_trans_commands": [command_pair[0] for command_pair in trans_res_dict['llm_transd_commands']],
        'source_commands': trans_res_dict['source_commands'],
        'llm_origin_response': trans_res_dict['llm_origin_response'],
        'matched_commands': []
    }
    real_command_tree_path = os.path.join(real_command_tree_dir, f"{file_name}.json")
    real_config_path = os.path.join(real_config_dir, f"{file_name}.txt")

    with open(real_command_tree_path, encoding='utf-8') as f:
        real_command_tree = json.load(f)
    with open(real_config_path, encoding='utf-8') as f:
        real_config = f.read()

    real_config = merge_simple_config(real_config)
    expected_commands = parse_config_file_content_intact(real_config)

    result_commands = parse_config_file_content_intact(trans_res_dict['trans_res'])
    expect_temp = get_all_templates(real_command_tree)
    evaluate_res['llm_command_ratio'] = len(trans_res_dict['llm_transd_commands']) / len(
        trans_res_dict['all_transd_commands'])
    evaluate_res['heuristic_command_ratio'] = len(trans_res_dict['heuristic_transd_commands']) / len(
        trans_res_dict['all_transd_commands'])
    llm_transd_commands = [command_pair[0] for command_pair in trans_res_dict['llm_transd_commands']]
    match_ratio_dict = command_template_process(expect_temp,
                                                deepcopy(result_commands),
                                                deepcopy(llm_transd_commands),
                                                deepcopy(expected_commands),
                                                real_command_tree)

    evaluate_res['llm_command_accuracy'] = match_ratio_dict['llm_command_match_ratio']

    evaluate_res['missed_commands'] = match_ratio_dict['missed_commands']
    evaluate_res['command_accuracy'] = match_ratio_dict['command_match_ratio']

    expected_templates = get_all_templates(real_command_tree)

    evaluate_res['missed_templates'] = match_ratio_dict['missed_templates']
    evaluate_res['grammatical_accuracy'] = match_ratio_dict['template_match_ratio']

    evaluate_res['matched_commands'] = match_ratio_dict['matched_commands']

    # 提取 source_cmds 和 target_cmds 为字典，方便查找
    source_cmds_dict = {item['id']: item['text'] for item in trans_res_dict['trans_mapping_info']['source_cmds']}
    target_cmds_dict = {item['id']: item['text'] for item in trans_res_dict['trans_mapping_info']['target_cmds']}

    # 生成 text,text 配对数据
    trans_mapping_pairs = {
        "all_trans_mapping": [],
        "llm_right_trans_mapping": [],
    }
    for edge in trans_res_dict['trans_mapping_info']['edges']:
        source_id = edge['source']
        target_id = edge['target']
        source_text = source_cmds_dict.get(source_id, '')
        target_text = target_cmds_dict.get(target_id, '')
        trans_mapping_pairs['all_trans_mapping'].append([source_text, target_text])
        if target_text in evaluate_res['matched_commands'] and source_text in evaluate_res['command_for_llm']:
            trans_mapping_pairs['llm_right_trans_mapping'].append([source_text, target_text])

    tran_temp_output_path = os.path.join(output_dir, target_vendor, f"{file_name}_temp.json")
    expected_temp_path = os.path.join(output_dir, target_vendor, f"{file_name}_expected_temp.json")

    label_config_text_path = os.path.join(output_dir, target_vendor, f"{file_name}_label_text.txt")
    source_config_command_tree_path = os.path.join(output_dir, target_vendor, f"{file_name}_source_command_tree.json")
    label_command_tree_path = os.path.join(output_dir, target_vendor, f"{file_name}_label_command_tree.json")
    tran_map_rule_usage_output_path = os.path.join(output_dir, target_vendor, f"{file_name}_map_rules.json")
    tran_evaluate_output_path = os.path.join(output_dir, target_vendor, f"{file_name}_evaluate.json")
    trans_mapping_path = os.path.join(output_dir, target_vendor, f"{file_name}_trans_mapping.json")

    with open(tran_res_output_path, 'w', encoding='utf-8') as f:
        f.write(trans_res_dict['trans_res'])
    with open(tran_temp_output_path, 'w', encoding='utf-8') as f:
        json.dump(trans_res_dict['trans_templates'], f, ensure_ascii=False, indent=4)
    with open(expected_temp_path, 'w', encoding='utf-8') as f:
        json.dump(expected_templates, f, ensure_ascii=False, indent=4)
    with open(label_config_text_path, mode='w', encoding='utf-8') as f:
        f.write(real_config)
    with open(source_config_command_tree_path, mode='w', encoding='utf-8') as f:
        json.dump(unified_json_config, f, ensure_ascii=False, indent=4)
    with open(label_command_tree_path, mode='w', encoding='utf-8') as f:
        json.dump(real_command_tree, f, ensure_ascii=False, indent=4)
    with open(tran_map_rule_usage_output_path, 'w', encoding='utf-8') as f:
        json.dump(trans_res_dict['map_rule_freq'], f, ensure_ascii=False, indent=4)
    with open(tran_evaluate_output_path, 'w', encoding='utf-8') as f:
        json.dump(evaluate_res, f, ensure_ascii=False, indent=4)
    with open(trans_mapping_path, mode='w', encoding='utf-8') as f:
        json.dump(trans_mapping_pairs, f, ensure_ascii=False, indent=4)
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
    name = 'all_data_2800'
    data_dir = 'valid_data_100_from_all'
    # data_dir = 'valid_data2'
    # data_dir = 'debug_data'
    config_num = ['valid_data_100_from_rag']
    # config_num = [500]
    # config_num = ['debug_data']

    manual_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/manual_mapping/{{}}_{{}}.json'
    llm_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/llm_mapping/{{}}_{{}}.json'
    templates_path = f'../dataset_multi_vendor_config/config_command_node/{name}/{{}}.json'
    error_mapping_path = f'../dataset_multi_vendor_config/mapping_template_library/error_mapping/{{}}_{{}}.json'

    vendors = ["Cisco", "Juniper", "HUAWEI"]
    output_dir = f'../experiment/exper_data/translated_config_with_{name}'
    local_EMmodel_path = '../EmbeddingModel/MiniLM-L6-v2'
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": device})

    for scale in config_num:
        mapping_library_path = f'../dataset_multi_vendor_config/mapping_template_library/{name}/{{}}_{{}}.json'
        module_match_path = f'../dataset_multi_vendor_config/mapping_template_library/{name}/{{}}_{{}}_module_match.json'
        config_model_dir = f'../dataset_multi_vendor_config/config_model/{name}/{{}}.json'

        for source_vendor in vendors:
            for target_vendor in vendors:
                if source_vendor == target_vendor:
                    continue
                if source_vendor!='Juniper' or target_vendor!='HUAWEI':
                    continue
                source_config_dir = f'../experiment/test_dataset/{data_dir}/command_tree/{source_vendor}' if source_vendor != 'Juniper' else f'../experiment/test_dataset/{data_dir}/command_tree/Juniper_subdivided'
                real_config_dir = f'../experiment/test_dataset/{data_dir}/text_config/{target_vendor}'
                real_command_tree_dir = f'../experiment/test_dataset/{data_dir}/command_tree/{target_vendor}'

                output_save_dir = os.path.join(output_dir, str(scale), source_vendor)
                os.makedirs(output_save_dir, exist_ok=True)
                delete_outdate_files(os.path.join(output_dir, str(scale), source_vendor, target_vendor))

                print(f"exper for {scale}, {source_vendor} to {target_vendor} translation with llm")

                mapping_libraries = {
                    "llm_mapping": {"Cisco_HUAWEI": {},
                                    "Cisco_Juniper": {},
                                    "HUAWEI_Cisco": {},
                                    "HUAWEI_Juniper": {},
                                    "Juniper_HUAWEI": {},
                                    "Juniper_Cisco": {}},
                    "Cisco_HUAWEI": {},
                    "Cisco_Juniper": {},
                    "HUAWEI_Cisco": {},
                    "HUAWEI_Juniper": {},
                    "Juniper_HUAWEI": {},
                    "Juniper_Cisco": {},
                }
                # mapping_libraries = mapping_library_load(mapping_library_path, vendors)

                config_matchers = config_matchers_load(templates_path, config_model_dir, module_match_path, vendors)

                config_models = config_model_load(config_model_dir, vendors)

                # translation_llm = Translation_Model('aliyun_deepseek-v3', config_model_dir=config_model_dir,
                #                                     vendors=vendors)

                translation_llm = Translation_Model('deepseek-chat', config_model_dir, vendors)

                config_translater = Config_Translater(mapping_libraries, config_matchers,
                                                      translation_llm, embedding_model, config_models)
                # 执行批量翻译
                batch_translate(config_translater, source_config_dir, output_save_dir, real_config_dir,
                                real_command_tree_dir,
                                source_vendor=source_vendor,
                                target_vendor=target_vendor)


if __name__ == "__main__":
    main()
