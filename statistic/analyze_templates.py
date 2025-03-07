# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/7 16:45
@Auth ： xiaolongtuan
@File ：analyze_templates.py
"""
# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/7 16:45
@Auth ： xiaolongtuan
@File ：analyze_templates.py
"""
import os
import json
from collections import defaultdict


def analyze_templates(config_dir, vendor):
    template_counter = defaultdict(int)
    total_templates = 0
    total_files = 0
    unvalid_files = 0
    # 遍历指定供应商的配置文件
    vendor_dir = os.path.join(config_dir, vendor)
    for filename in os.listdir(vendor_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(vendor_dir, filename)
            total_files += 1


            with open(filepath, 'r') as f:
                try:
                    data = json.load(f)
                except:
                    continue
                # 遍历所有节点
                for node in data.values():
                    if not isinstance(node, dict):
                        unvalid_files += 1
                        break

                    # 统计模板使用次数
                    if 'template' in node:
                        template_counter[node['template']] += 1
                        total_templates += 1
                    # 处理嵌套节点
                    for sub_node in node.values():
                        if isinstance(sub_node, dict) and 'template' in sub_node:
                            template_counter[sub_node['template']] += 1
                            total_templates += 1

    # 计算概率
    template_stats = {}
    template_stats['valid_file_rate'] = f"{((total_files - unvalid_files) / total_files) * 100:.2f}"
    template_stats['total_templates_used'] = total_templates
    template_stats['templates'] = []
    for template, count in template_counter.items():
        probability = count / total_templates
        template_stats['templates'].append((template, {
            'count': count,
            'probability': round(probability, 4)
        }))
    # 按照使用次数排序template_stats['templates']
    template_stats['templates'].sort(key=lambda x: x[1]['count'], reverse=True)


    return template_stats


if __name__ == "__main__":
    config_dir = "../dataset_multi_vendor_config/Json_config"
    vendors =["Cisco","HUAWEI","Juniper"]
    for vendor in vendors:
        stats = analyze_templates(config_dir, vendor)
        # print("模板使用统计结果：")
        # print("有效文件比例：", stats['valid_file_rate'])
        # for template, data in stats['templates']:
        #     print(f"模板: {template}")
        #     print(f"  使用次数: {data['count']}")
        #     print(f"  使用概率: {data['probability']:.2%}")
        #     print("-------------------")
        # 将统计结果保存为 JSON 文件
        with open(f"./statistic_res/{vendor}_template_stats.json", 'w') as f:
            json.dump(stats, f, indent=4)
