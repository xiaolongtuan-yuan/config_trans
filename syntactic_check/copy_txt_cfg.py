import os
import shutil
range_num = 2000
file_range = 'config_data_2800'
# file_name_path = 'config_trans/dataset_multi_vendor_config/config_data_400/Juniper/'
# file_name_path = 'config_trans/dataset_multi_vendor_config/config_data_1200/Juniper/'
# file_name_path = 'config_trans/dataset_multi_vendor_config/config_data_2800/Juniper/'
file_name_path = f'config_trans/dataset_multi_vendor_config/{file_range}/Juniper/'



# 遍历源文件夹下所有.txt文件
for vendor in ['Cisco', 'HUAWEI','Juniper']:
    # 源文件夹和目标文件夹
    source_folder = f'config_trans/dataset_multi_vendor_config/{file_range}/{vendor}/'
    for filename in os.listdir(file_name_path):
        if filename.endswith('.txt'):
            source_path = os.path.join(source_folder, filename)
            target_folder = f'syntactic_check/config_data_{range_num}/{vendor}_config/{vendor}_{os.path.splitext(filename)[0]}/configs/'
            # 确保目标文件夹存在
            os.makedirs(target_folder, exist_ok=True)
            # 修改文件后缀为.cfg
            new_filename = os.path.splitext(filename)[0] + '.cfg'
            target_path = os.path.join(target_folder, new_filename)
            # 复制并改名
            shutil.copy2(source_path, target_path)

    print(f"{vendor}文件复制并改名完成！")


# 原1600-1999文件夹下的txt文件复制到新的文件夹下
'''vendors = ['cisco', 'huawei','juniper']
ture_vendors = ['Cisco', 'HUAWEI','Juniper']

file_name_path = 'config_trans/dataset_multi_vendor_config/config_data_2000/'

for k in range(len(vendors)):
    for i in range(1600, 2000):
        # 源文件夹
        vendor = vendors[k]
        source_folder = file_name_path + f'{i}/{vendor}/'
        for filename in os.listdir(source_folder):
            # print(filename)
            if filename.endswith('.txt'):
                source_path = os.path.join(source_folder, filename)
                print(source_path)
                vendor_name = ture_vendors[k]
                target_folder = f'syntactic_check/config_data_{range_num}/{vendor_name}_config/{vendor_name}_{os.path.splitext(filename)[0]}/configs/'
                # 确保目标文件夹存在
                os.makedirs(target_folder, exist_ok=True)
                # 修改文件后缀为.cfg
                new_filename = os.path.splitext(filename)[0] + '.cfg'
                target_path = os.path.join(target_folder, new_filename)
                # 复制并改名
                shutil.copy2(source_path, target_path)
    print(f"{vendor}文件复制并改名完成！")'''
