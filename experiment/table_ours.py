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
    cul_grammatical_accuracy_with_json, cul_device_grammatical_accuracy_with_json, cul_command_and_param_accuracy, \
    cuL_llm_accuracy_with_json, cuL_llm_coverage_with_json

if __name__ == '__main__':
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    name = 'full_process'
    data_dir = 'valid_data'
    scales = [2800]

    # translated_config_base = '../experiment/exper_data/translated_config_with_multi_module'
    translated_config_base = f'../experiment/exper_data/translated_config_with_{name}'
    vendor_config_models = {}
    for vendor in vendors:
        config_model_path = f'../dataset_multi_vendor_config/config_model/verified_data/{vendor}.json'
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
            "llm_command_accuracy": {
                "vendors": [],
                "average": 0,
            },
            "rule_command_accuracy": {
                "vendors": [],
                "average": 0,
            },
            "rule_LLM_coverage": {
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

                trannlated_config_files = [f for f in os.listdir(translated_config_dir) if
                                           f.endswith('.txt') and not f.endswith('text.txt')]
                real_config_dir = f'../experiment/test_dataset/{data_dir}/text_config/{target_vendor}'
                real_target_config_json_dir = f'../experiment/test_dataset/{data_dir}/command_tree/{target_vendor}'

                accuracy_dict = cul_command_and_param_accuracy(
                    translated_config_dir, real_config_dir, real_target_config_json_dir, trannlated_config_files)

                rule_LLM_coverage = cuL_llm_coverage_with_json(f'../experiment/test_dataset/{data_dir}/text_config/{source_vendor}',
                    translated_config_dir, trannlated_config_files)
                exper_data['rule_LLM_coverage']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', rule_LLM_coverage))

                semantic_similarity = compute_embded_similarity(translated_config_dir, real_config_dir,
                                                                trannlated_config_files)
                exper_data['semantic_similarity']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', semantic_similarity))

                exper_data['command_accuracy']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', accuracy_dict['average_command_match_ratio']))
                exper_data['rule_command_accuracy']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', accuracy_dict['average_rule_command_match_ratio']))

                exper_data['llm_command_accuracy']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', accuracy_dict['average_llm_command_match_ratio']))

                exper_data['param_accuracy']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', accuracy_dict['average_param_match_ratio']))

                exper_data['grammatical_accuracy']['vendors'].append(
                    (f'{source_vendor}_{target_vendor}', accuracy_dict['average_template_match_ratio']))

                view_accuracy = cul_view_accuracy(translated_config_dir, trannlated_config_files,
                                                  vendor_config_models[target_vendor])
                exper_data['view_accuracy']['vendors'].append((f'{source_vendor}_{target_vendor}', view_accuracy))

        exper_data['semantic_similarity']['average'] = sum(
            [x[1] for x in exper_data['semantic_similarity']['vendors']]) / len(
            exper_data['semantic_similarity']['vendors'])
        exper_data['command_accuracy']['average'] = sum(
            [x[1] for x in exper_data['command_accuracy']['vendors']]) / len(exper_data['command_accuracy']['vendors'])
        exper_data['rule_LLM_coverage']['average'] = sum(
            [x[1] for x in exper_data['rule_LLM_coverage']['vendors']]) / len(
            exper_data['rule_LLM_coverage']['vendors'])
        exper_data['llm_command_accuracy']['average'] = sum(
            [x[1] for x in exper_data['llm_command_accuracy']['vendors']]) / len(
            exper_data['llm_command_accuracy']['vendors'])
        exper_data['rule_command_accuracy']['average'] = sum(
            [x[1] for x in exper_data['rule_command_accuracy']['vendors']]) / len(
            exper_data['rule_command_accuracy']['vendors'])
        exper_data['param_accuracy']['average'] = sum(
            [x[1] for x in exper_data['param_accuracy']['vendors']]) / len(exper_data['param_accuracy']['vendors'])
        exper_data['grammatical_accuracy']['average'] = sum(
            [x[1] for x in exper_data['grammatical_accuracy']['vendors']]) / len(
            exper_data['grammatical_accuracy']['vendors'])
        exper_data['view_accuracy']['average'] = sum([x[1] for x in exper_data['view_accuracy']['vendors']]) / len(
            exper_data['view_accuracy']['vendors'])
        print(f"finished {name} evaluation")
        print(exper_data)
        with open(f'../experiment/exper_res/res_ours_{name}.json', 'w', encoding='utf-8') as f:
            json.dump(exper_data, f, indent=4)
