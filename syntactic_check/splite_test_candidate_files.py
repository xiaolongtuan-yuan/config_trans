# -*- coding: utf-8 -*-
"""
@Time ： 2025/6/13 21:33
@Auth ： xiaolongtuan
@File ：splite_test_candidate_files.py
"""
import json

def compare_config_lines(current_file_path, old_file_path, row_num=5) -> set:
    # 读取当前配置文件
    with open(current_file_path, 'r', encoding='utf-8') as f:
        current_data = json.load(f)

    # 读取旧版配置文件
    with open(old_file_path, 'r', encoding='utf-8') as f:
        old_data = json.load(f)

    candidate_vendor_file = {}
    for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
        candidate_vendor_file[vendor] = set()
        # 获取 Cisco 部分的 all_config_line
        current_all_config = current_data.get(vendor, {}).get('test_config_line', {})
        old_all_config = old_data.get(vendor, {}).get('all_config_line', {})

        # 存储行数相差小于 5 的文件名列表
        for filename, current_lines in current_all_config.items():
            old_lines = old_all_config.get(filename)
            if old_lines is not None:
                diff = abs(current_lines - old_lines)
                if diff <= row_num:
                    candidate_vendor_file[vendor].add(filename)

    candidate_vendor_file['all'] = candidate_vendor_file['Cisco'] & candidate_vendor_file['HUAWEI'] & candidate_vendor_file['Juniper']
    return candidate_vendor_file['all']

if __name__ == '__main__':
    candidate_files = {}
    candidate_files_set = set()
    row_num= 2
    candidate_files['diff_row_nums'] = row_num
    for range_num in ['400', '1200', '2000', '2800']:
        current_file_path = f'./config_data_{range_num}/error_info/config_lines.json'
        old_file_path = f'./config_data_{range_num}_0501/error_info/config_lines.json'

        result = compare_config_lines(current_file_path, old_file_path, row_num=row_num)
        rest = result - candidate_files_set
        candidate_files[range_num] = list(rest)
        candidate_files_set.update(rest)
        # 输出结果
        print(f"there have {len(candidate_files_set)} for test")
    with open('./candidate_file_names/candidate_file_names.json', 'w', encoding='utf-8') as f:
        json.dump(candidate_files, f, ensure_ascii=False, indent=4)