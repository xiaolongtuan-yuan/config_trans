# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/7 13:52
@Auth ： xiaolongtuan
@File ：test_parse_1.py
"""
from pathlib import Path
from src import load_client, process_file

def test_parse_single_file(vendor, config_path, target_file):
    model_name = "deepseek-chat"
    client = load_client(model_name, endpoint_url='https://api.deepseek.com/v1')

    full_config_path = Path('../dataset_multi_vendor_config') / config_path / vendor
    save_path = Path('test_res/Json_config') / vendor

    # 确保保存路径存在
    save_path.mkdir(parents=True, exist_ok=True)

    # 处理指定文件
    process_file(target_file, str(full_config_path), str(save_path), vendor, client, model_name)
    print(f"文件 {target_file} 解析完成，结果已保存至 {save_path}")


if __name__ == "__main__":
    # 直接为参数赋值
    vendor = "Juniper"
    config_path = "config_data_801-1200"
    target_file = "vrp_te-p2p_0139_0.txt"

    test_parse_single_file(vendor, config_path, target_file)
