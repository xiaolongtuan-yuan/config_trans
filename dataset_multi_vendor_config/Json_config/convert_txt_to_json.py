# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/21 15:23
@Auth ： xiaolongtuan
@File ：convert_txt_to_json.py
"""
import json
from pathlib import Path


def convert_txt_to_json(directory):
    folder = Path(directory)
    txt_files = list(folder.rglob('*.txt'))

    for txt_file in txt_files:
        json_file = txt_file.with_suffix('.json')
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            try:
                # 判断content是否是有效的json字符串
                json.loads(content)
                with open(json_file, 'w', encoding='utf-8') as f:
                    f.write(content)
        except json.JSONDecodeError:
        print(txt_file)
        continue


# 转换Json_config/Cisco目录下的txt文件为json
for vendor in ['Cisco', 'HUAWEI', "Juniper"]:
    directory = f'./{vendor}'
    convert_txt_to_json(directory)
