import os
import shutil


# 遍历源文件夹下所有.txt文件
for vendor in ['Cisco', 'Juniper']:
    # 源文件夹和目标文件夹
    source_folder = f'experiment/test_dataset/text_config/{vendor}/'
    for filename in os.listdir(source_folder):
        if filename.endswith('.txt'):
            source_path = os.path.join(source_folder, filename)
            target_folder = f'syntactic_check/configuration/{vendor}_config/{vendor}_{os.path.splitext(filename)[0]}/configs/'
            # 确保目标文件夹存在
            os.makedirs(target_folder, exist_ok=True)
            # 修改文件后缀为.cfg
            new_filename = os.path.splitext(filename)[0] + '.cfg'
            target_path = os.path.join(target_folder, new_filename)
            # 复制并改名
            shutil.copy2(source_path, target_path)

    print(f"{vendor}文件复制并改名完成！")