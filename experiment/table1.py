# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/5 23:41
@Auth ： xiaolongtuan
@File ：table1.py
"""
import json
import os

import sys
# 获取当前脚本的绝对路径
current_script_path = os.path.abspath(__file__)
# 获取项目根目录（假设 config_trans 是项目根目录）
project_root = os.path.dirname(os.path.dirname(current_script_path))  # 上两级目录
# 添加到 Python 模块搜索路径
sys.path.append(project_root)

from experiment.compute_bleu import compute_embded_similarity
from experiment.syntax_correctness import load_config_model, cul_view_accuracy
from experiment.tree_match import cul_command_accuracy, cul_grammatical_accuracy, cul_param_accuracy

if __name__ == '__main__':
    e2e_models = ["aliyun_deepseek-r1", "gpt-4o", "aliyun_qwen-max"]
    for e2e_model in e2e_models:
        vendors = ['Cisco', 'HUAWEI', 'Juniper']
        translated_config_base = './exper_data/e2e_llm_translated_config'
        vendor_config_models = {}
        for vendor in vendors:
            config_model_path = f'../dataset_multi_vendor_config/config_model/verified_data/{vendor}.json'
            config_model = load_config_model(config_model_path)
            vendor_config_models[vendor] = config_model

        exper_data = {
            "semantic_similarity": {
                "vendors": [],
                "average": 0,
            },
            "command_accuracy": {
                "vendors": [],
                "average": 0,
            },
            "param_accuracy": {
                "vendors": [],
                "average": 0,
            },
            "grammatical_accuracy": {
                "vendors": [],
                "average": 0,
            },
            "view_accuracy": {
                "vendors": [],
                "average": 0,
            }
        }
        for source_vendor in vendors:
            for target_vendor in vendors:
                if target_vendor == source_vendor:
                    continue

                translated_config_dir = os.path.join(translated_config_base, e2e_model, source_vendor, target_vendor)
                trannlated_config_files = [f for f in os.listdir(translated_config_dir) if f.endswith('.txt')][:100]
                real_config_dir = f'./test_dataset/valid_data/text_config/{target_vendor}'

                semantic_similarity = compute_embded_similarity(translated_config_dir, real_config_dir,
                                                                trannlated_config_files)     # cul semantic_similarity
                exper_data['semantic_similarity']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', semantic_similarity))

                command_accuracy = cul_command_accuracy(translated_config_dir, real_config_dir, trannlated_config_files)    # cul command accuracy

                exper_data['command_accuracy']['vendors'].append((f'{source_vendor}_{target_vendor}', command_accuracy))

                param_accuracy = cul_param_accuracy(translated_config_dir, real_config_dir, trannlated_config_files,
                                                       vendor_config_models[target_vendor])                                 # cul param accuracy
                exper_data['param_accuracy']['vendors'].append((f'{source_vendor}_{target_vendor}', param_accuracy))

                grammatical_accuracy = cul_grammatical_accuracy(translated_config_dir, real_config_dir,
                                                                trannlated_config_files,
                                                                vendor_config_models[target_vendor])                        # cul grammatical accuracy
                exper_data['grammatical_accuracy']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', grammatical_accuracy))



                view_accuracy = cul_view_accuracy(translated_config_dir, trannlated_config_files,
                                                  vendor_config_models[target_vendor])                                      # cul view accuracy
                exper_data['view_accuracy']['vendors'].append((f'{source_vendor}_{target_vendor}', view_accuracy))
        # 计算平均值
        exper_data['semantic_similarity']['average'] = sum(
            [x[1] for x in exper_data['semantic_similarity']['vendors']]) / len(
            exper_data['semantic_similarity']['vendors'])
        exper_data['command_accuracy']['average'] = sum(
            [x[1] for x in exper_data['command_accuracy']['vendors']]) / len(exper_data['command_accuracy']['vendors'])
        exper_data['param_accuracy']['average'] = sum(
            [x[1] for x in exper_data['param_accuracy']['vendors']]) / len(exper_data['param_accuracy']['vendors'])
        exper_data['grammatical_accuracy']['average'] = sum(
            [x[1] for x in exper_data['grammatical_accuracy']['vendors']]) / len(
            exper_data['grammatical_accuracy']['vendors'])
        exper_data['view_accuracy']['average'] = sum([x[1] for x in exper_data['view_accuracy']['vendors']]) / len(
            exper_data['view_accuracy']['vendors'])

        with open(f'./exper_res/res_{e2e_model}.json', 'w', encoding='utf-8') as f:
            json.dump(exper_data, f, indent=4)
