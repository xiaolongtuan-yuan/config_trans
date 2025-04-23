# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/5 23:41
@Auth ： xiaolongtuan
@File ：table1.py
"""
import json
import os
import sys
sys.path.append("/data/public/hrx/Repositories/config_trans")
import experiment

from experiment.compute_bleu import compute_embded_similarity
from experiment.syntax_correctness import load_config_model, cul_view_accuracy
from experiment.tree_match import cul_command_accuracy, cul_grammatical_accuracy, cul_param_accuracy, \
    cul_grammatical_accuracy_with_json

if __name__ == '__main__':
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    scales = [388]

    translated_config_base = './exper_data/translated_config_with_scale388en'
    vendor_config_models = {}
    for vendor in vendors:
        config_model_path = f'../dataset_multi_vendor_config/config_model/scale388en/{vendor}_388.json'
        config_model = load_config_model(config_model_path)
        vendor_config_models[vendor] = config_model

    for scale in scales:
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

                translated_config_dir = os.path.join(translated_config_base, str(scale), source_vendor, target_vendor)


                trannlated_config_files = [f for f in os.listdir(translated_config_dir) if f.endswith('.txt') and not f.endswith('text.txt')]
                real_config_dir = f'./test_dataset/text_config/{target_vendor}'

                # semantic_similarity = compute_embded_similarity(translated_config_dir, real_config_dir,
                #                                                 trannlated_config_files)
                # exper_data['semantic_similarity']['vendors'].append(
                #     (f'{source_vendor}_{target_vendor}', semantic_similarity))

                command_accuracy = cul_command_accuracy(translated_config_dir, real_config_dir, trannlated_config_files)
                exper_data['command_accuracy']['vendors'].append((f'{source_vendor}_{target_vendor}', command_accuracy))

                param_accuracy = cul_param_accuracy(translated_config_dir, real_config_dir, trannlated_config_files,
                                                    vendor_config_models[target_vendor])
                exper_data['param_accuracy']['vendors'].append((f'{source_vendor}_{target_vendor}', param_accuracy))

                real_target_config_json_dir = f'./exper_data/{target_vendor}' if target_vendor != 'Juniper' else f'./exper_data/Juniper_subdivided'

                grammatical_accuracy = cul_grammatical_accuracy_with_json(translated_config_dir, real_target_config_json_dir,
                                                                trannlated_config_files)

                exper_data['grammatical_accuracy']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', grammatical_accuracy))

                view_accuracy = cul_view_accuracy(translated_config_dir, trannlated_config_files,
                                                  vendor_config_models[target_vendor])
                exper_data['view_accuracy']['vendors'].append((f'{source_vendor}_{target_vendor}', view_accuracy))
        # 计算平均值
        # exper_data['semantic_similarity']['average'] = sum(
        #     [x[1] for x in exper_data['semantic_similarity']['vendors']]) / len(
        #     exper_data['semantic_similarity']['vendors'])
        exper_data['command_accuracy']['average'] = sum(
            [x[1] for x in exper_data['command_accuracy']['vendors']]) / len(exper_data['command_accuracy']['vendors'])
        exper_data['param_accuracy']['average'] = sum(
            [x[1] for x in exper_data['param_accuracy']['vendors']]) / len(exper_data['param_accuracy']['vendors'])
        exper_data['grammatical_accuracy']['average'] = sum(
            [x[1] for x in exper_data['grammatical_accuracy']['vendors']]) / len(
            exper_data['grammatical_accuracy']['vendors'])
        exper_data['view_accuracy']['average'] = sum([x[1] for x in exper_data['view_accuracy']['vendors']]) / len(
            exper_data['view_accuracy']['vendors'])
        print(f"finished {scale} evaluation")
        print(exper_data)
        with open(f'./exper_res/res_heuristics_{scale}.json', 'w', encoding='utf-8') as f:
            json.dump(exper_data, f, indent=4)
