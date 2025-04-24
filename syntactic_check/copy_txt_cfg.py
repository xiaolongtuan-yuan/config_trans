import os
import shutil

file_name_path = 'config_trans/dataset_multi_vendor_config/config_data_1-400/Juniper/'

# 遍历源文件夹下所有.txt文件
for vendor in ['Cisco', 'HUAWEI','Juniper']:
    # 源文件夹和目标文件夹
    source_folder = f'config_trans/dataset_multi_vendor_config/config_data_1-400/{vendor}/'
    for filename in os.listdir(file_name_path):
        if filename.endswith('.txt'):
            source_path = os.path.join(source_folder, filename)
            target_folder = f'syntactic_check/config_data_400/{vendor}_config/{vendor}_{os.path.splitext(filename)[0]}/configs/'
            # 确保目标文件夹存在
            os.makedirs(target_folder, exist_ok=True)
            # 修改文件后缀为.cfg
            new_filename = os.path.splitext(filename)[0] + '.cfg'
            target_path = os.path.join(target_folder, new_filename)
            # 复制并改名
            shutil.copy2(source_path, target_path)

    print(f"{vendor}文件复制并改名完成！")