from pathlib import Path
import json

# 读取txt文件
def txtTojson(file_name):
    with open('{}.txt'.format(file_name), 'r', encoding='utf-8') as f:
        data = json.load(f)  # 直接作为json加载

    # 写入json文件
    with open('{}.json'.format(file_name), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_txt_filenames(folder_path):
    folder = Path(folder_path)
    txt_filenames = [str(file.name) for file in folder.rglob('*.txt')]
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
    folder_path = 'Cisco/'
    txt_filenames = get_txt_filenames(folder_path)
    result = abstract_configModule(txt_filenames)
    print(len(result), '\n', result)