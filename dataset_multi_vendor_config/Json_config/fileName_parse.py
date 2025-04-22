from pathlib import Path
import json
import os
# 读取txt文件
def txtTojson(file_name):
    with open('{}.txt'.format(file_name), 'r', encoding='utf-8') as f:
        data = json.load(f)  # 直接作为json加载

    # 写入json文件
    with open('{}.json'.format(file_name), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_txt_filenames(folder_path):
    folder = Path(folder_path)
    txt_filenames = [file.stem for file in folder.rglob('*.json')]
    return txt_filenames


'''filenames = [
    "cfg_dsvpn_0015_00_0.txt",
    "hw_NE40E_V800R012C10.log",
    "test_abc_123_45.txt"
]'''

def abstract_configModule(filenames):
    # 提取逻辑
    results = []
    for filename in filenames:
        parts = filename.split('_')        # 按 _ 分割字符串
        if len(parts) >= 3:               # 确保至少有2个 _ 分割的部分
            target = parts[1]             # 取第二个部分（索引从0开始）
            results.append(target)
        else:
            results.append(None)          # 处理不符合格式的文件名

    return set(results)
    # print(results)  # 输出: ['dsvpn', 'NE40E', 'abc']

if __name__ == "__main__":
    folder_path = 'Json_config/Juniper_simplified'
    txt_filenames = get_txt_filenames(folder_path)[:388]
    print(len(txt_filenames), '\n', sorted(txt_filenames))
    error_filename_path = 'error_file_record/error_cisco.json'
    with open(error_filename_path, 'r', encoding='utf-8') as f:
        error_filenames = json.load(f)  # 直接作为json加载
        
    clean_names = [os.path.splitext(name)[0] for name in error_filenames]
    correct_filenames = list(set(txt_filenames[:388]) - set(clean_names))
    print(len(correct_filenames), '\n', sorted(correct_filenames))
    # 写入json文件
    test_filenames = 'Json_config/test_filenames.json'
    with open(test_filenames, 'w', encoding='utf-8') as f:
        json.dump(sorted(correct_filenames), f, ensure_ascii=False, indent=4)
    # result = abstract_configModule(txt_filenames)
    # print(len(result), '\n', result)