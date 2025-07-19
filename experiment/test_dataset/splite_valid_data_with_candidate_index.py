import json
import os
import random
import shutil

random.seed(42)


with open('../../syntactic_check/candidate_file_names/candidate_file_names.json', 'r') as f:
    candidate_file_names = set()
    candidate_file_names_dic = json.load(f)
    for num in ['400', '1200', '2000', '2800']:
        candidate_file_names.update(candidate_file_names_dic[num])

candidate_file_names = list(candidate_file_names)

print(f'there all file nums: {len(candidate_file_names)}')

target_dir = 'valid_data_all_from_all'
if os.path.exists(target_dir):
    shutil.rmtree(target_dir)

valid_devices = []
for device in candidate_file_names:
    flag = True
    for vendor in ['Cisco', 'HUAWEI', 'Juniper']:
        command_tree = f'command_tree/{vendor}/{device}.json'
        Json_simplified = f'Json_simplified/{vendor}/{device}.json'
        text_config = f'text_config/{vendor}/{device}.txt'

        for focus_dir in [command_tree, Json_simplified, text_config]:
            if not os.path.exists(os.path.join('all_data', focus_dir)):
                flag = False
                break
    if flag:
        valid_devices.append(device)
        # if len(valid_devices) == 100: break

for device in valid_devices:
    for vendor in ['Cisco', 'HUAWEI', 'Juniper', 'Juniper_subdivided']:
        command_tree = f'command_tree/{vendor}/{device}.json'
        Json_simplified = f'Json_simplified/{vendor}/{device}.json'
        text_config = f'text_config/{vendor}/{device}.txt'

        for focus_dir in [command_tree, Json_simplified, text_config]:
            if os.path.exists(os.path.join('all_data', focus_dir)):
                # 复制
                os.makedirs('/'.join(f'{target_dir}/{focus_dir}'.split('/')[:-1]), exist_ok=True)
                os.system(f'cp all_data/{focus_dir} {target_dir}/{focus_dir}')

print(f'sample data: {len(valid_devices)}')




