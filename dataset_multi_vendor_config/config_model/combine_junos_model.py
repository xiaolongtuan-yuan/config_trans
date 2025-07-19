# -*- coding: utf-8 -*-
"""
@Time ： 2025/5/10 22:01
@Auth ： xiaolongtuan
@File ：combine_junos_model.py
用于将视图拆分后的Juniper命令合并为完整的命令，得到完整的juniper模型，便于与txt文件进行对比
"""
import json

model_dir = 'all_data_2800'

combine_model = {}
# for scale in [40, 80, 120]:
with open(f'./{model_dir}/Juniper.json', 'r', encoding='utf-8') as f:
    juniper_model = json.load(f)

for root, value in juniper_model.items():
    flag = True
    root_parameter = value.get('parameters')
    for sub_command, v in value.items():
        if isinstance(v, dict):
            combine_command = root + ' ' + sub_command
            total_parameters = root_parameter + v.get('parameters')
            combine_model[combine_command] = {
                'template': combine_command,
                'parameters': total_parameters
            }
            flag = False
    combine_model[root] = {
        'template': root,
        'parameters': root_parameter
    }

with open(f'./{model_dir}/Juniper_combined.json', 'w', encoding='utf-8') as f:
    json.dump(combine_model, f, ensure_ascii=False, indent=4)




