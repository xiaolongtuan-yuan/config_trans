import os
import shutil
import json
def copy_json_files(src_dir, dst_dir, filenames):
    # 确保目标目录存在
    os.makedirs(dst_dir, exist_ok=True)
    
    # 遍历源目录中的所有JSON文件
    for filename in filenames:

        src_path = os.path.join(src_dir, filename + '.json')
        dst_path = os.path.join(dst_dir, filename + '.json')
        shutil.copy(src_path, dst_path)
        print(f"Copied: {src_path} -> {dst_path}")

# 读取JSON文件名
filename_path = "experiment/exper_data/test_filenames.json"
with open(filename_path, 'r', encoding='utf-8') as f:
        filenames = json.load(f)  # 直接作为json加载

# 使用示例
src_dir = 'dataset_multi_vendor_config/Json_config/Juniper/'
dst_dir = 'experiment/exper_data/Juniper/'
copy_json_files(src_dir, dst_dir, filenames)