import json
from pathlib import Path
import os

def get_json_filenames(folder_path):
    folder = Path(folder_path)
    json_filenames = [file.stem for file in folder.rglob('*.json')]
    return json_filenames

def get_txt_filenames(folder_path):
    folder = Path(folder_path)
    json_filenames = [file.stem for file in folder.rglob('*.txt')]
    return json_filenames

def load_json_file(file_path):
    """加载JSON文件，如果解析失败则返回None"""
    try:
        with open(file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            return data
    except json.JSONDecodeError as e:
        print(f"警告: 无法解析JSON文件 {file_path}，错误: {e}")
        return None
    except FileNotFoundError:
        print(f"警告: 文件 {file_path} 不存在")
        return None
    except Exception as e:
        print(f"警告: 读取文件 {file_path} 时发生未知错误: {e}")
        return None

# save JSON file
def save_json_file(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

# 把commandtree中的模板全部提取出来
def extract_templates_from_commandtree(command_tree, templates):
    for key, sub_tree in command_tree.items():
        if key == 'template':
            command = command_tree['template']
            if command not in templates.keys():
                templates[command] = 1
            else:
                templates[command] += 1
        if not isinstance(sub_tree, dict):
            continue
        else:
            templates =  extract_templates_from_commandtree(sub_tree, templates)
    return templates

if __name__ == "__main__":
    file_num = 388
    # Example usage
    folder_path = 'dataset_multi_vendor_config/Json_config/Juniper_simplified'
    json_filenames = get_json_filenames(folder_path)

    # Load a JSON file and extract templates
    count = 0
    for filename in json_filenames[:file_num]:
        for vendor in ['HUAWEI', 'Cisco', 'Juniper']:
            file_path = f'dataset_multi_vendor_config/Json_config/{vendor}/{filename}.json'
            print(f"Extracted Templates from {file_path}")
            data = load_json_file(file_path)
            if data is None:
                print(f"跳过文件: {file_path}")
                continue  # 跳过无法解析的文件
            templates = {}
            templates = extract_templates_from_commandtree(data, templates)
            save_json_file(f'dataset_multi_vendor_config/Json_config/{vendor}_template/{filename}.json', templates)
        count += 1
        print(f"Processed {count} files")
    
    '''
    file_path = 'dataset_multi_vendor_config/Json_config/HUAWEI_simplified/ne_pppoe_0015_1.json'
    data = load_json_file(file_path)
    '''