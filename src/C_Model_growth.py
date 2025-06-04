'''
将训练数据集中的json文件合并为一个，作为该供应商的json文件，
'''
import json
from pathlib import Path
import os
from tqdm import tqdm
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def process_juniper_json(json_config):
    processed_json = {}
    for k, v in json_config.items():
        if 'template' in v:
            del v['template']
        if isinstance(v, dict):
            for command, info in v.items():
                processed_json[command] = info
    return processed_json

def merge_nodes(existing_node: dict, new_node: dict):
    """
    将 new_node 合并到 existing_node 中：
    - existing_node 已存在的键值不覆盖（只保留第一次出现节点）；
    - 如果键对应的 value 是一个 dict（子节点），递归合并；
    - 如果是任意其他类型且不存在于 existing_node，则直接添加。
    """
    for key, val in new_node.items():
        # 如果在 existing_node 中没有这个 key，直接添加
        if key not in existing_node:
            existing_node[key] = val
        else:
            # 若都为 dict，则需要递归合并，否则跳过（只保留第一次）
            if isinstance(existing_node[key], dict) and isinstance(val, dict):
                merge_nodes(existing_node[key], val)
            # 其余情况按照"保留第一次出现"的原则，不覆盖 existing_node[key]
    return existing_node

def check_template_duplication(command:str, template_re_libary:dict):
    """
    检查 template_re_libary 中是否存在相同的 能够匹配command 的正则表达式键，
    如果存在，则返回其对应的值，否则返回 None。
    """
    for regex, template_dict in template_re_libary.items():
        if regex.match(command):
            return template_dict, regex
    return None, None


def template_to_regex(template: str) -> re.Pattern:
    """
    将一个命令模板转换为正则表达式。
    示例：
      "binding tunnel [param1]" 转换为 r"^binding\s+tunnel\s+(\S+)$"
    """
    # 按空格分割模板
    tokens = template.split()
    regex_tokens = []

    for token in tokens:
        if token.startswith('[') and token.endswith(']'):
            # 如果是占位符，转换为捕获组，匹配一个非空字符串
            regex_tokens.append(r"(\S+)")
        else:
            # 固定部分，转义特殊字符后加入列表
            regex_tokens.append(re.escape(token))

    # 使用 \s+ 连接各个部分，表示各部分之间可以有一个或多个空白字符
    regex_pattern = r"^" + r"\s+".join(regex_tokens) + r"$"
    return re.compile(regex_pattern)

def placeholder_count(template: str):
    pattern = r'\[parameter\d+\]'
    # 查找所有匹配的占位符
    matches = re.findall(pattern, template)
    return len(matches)

def merge_models(config1, config2, vendor_command, template_used_statistic):
    """
    递归地将 config2 中不存在于 config1 的节点合并到 config1 中。
    如果 key 存在于 config1 且对应子节点都是字典，则继续合并其子节点；
    如果 key 不存在于 config1，则将 config2[key] 直接插入到 config1；
    如果 key 都存在，但对应的值不是字典，则保持 config1 原值不变（即不覆盖）。
    """
    for key, value in config2.items():
        if not isinstance(value, dict):
            continue
        
        required_fields = ["template", "command", "explanation", "parameters"]
        if isinstance(value, dict):
            if not all(field in value for field in required_fields):
                continue  # 跳过缺少字段的节点
        command_line = value.get("command")
        if command_line:
            try:
                if not placeholder_count(key) == len(value["parameters"]):  # llm解析时的错误
                    continue
            except:
                continue
            template_dict, regex = check_template_duplication(command_line, vendor_command)
            if template_dict:
                # 如果 vendor_command 中已经存在这个命令对应的模版, 选择具有最大参数的模版
                if len(value["parameters"]) <= len(template_dict['parameters']):# 需要模版库
                    value['template'] = template_dict['template']
                    key = template_dict['template']
                    value['parameters'] = template_dict['parameters']
                    template_used_statistic[key] += 1
                else:
                    # 更换regex
                    template_used_statistic[key] = template_used_statistic[template_dict['template']] + 1
                    del vendor_command[regex]
                    del template_used_statistic[template_dict['template']]

                    new_regex = template_to_regex(value['template'])
                    vendor_command[new_regex] = {k: value[k] for k in ['template', 'parameters'] if k in value}
            else:
                new_regex = template_to_regex(value['template'])
                vendor_command[new_regex] = {k: value[k] for k in ['template', 'parameters'] if k in value}
                template_used_statistic[value['template']] = 1

        if key not in config1:
            # 如果 config1 中没有该键，直接插入
            config1[key] = value
        else:
            # 如果 config1 中已经存在这个 key, 且双方都是 dict，则递归合并子节点
            if isinstance(value, dict) and len(value) > 4 and isinstance(config1[key], dict):
                merge_models(config1[key], value, vendor_command, template_used_statistic)
            # 如果不是 dict，则不覆盖，保持原值。
            # 所以这里什么都不做即可
    return config1


def get_json_filenames(folder_path):
    folder = Path(folder_path)
    json_filenames = [str(file.name) for file in folder.rglob('*.json')]
    return json_filenames


# load JSON fie and load data
def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data


# save JSON fie
def save_json_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as json_file:
        # json.dump(data, json_file, indent=4)
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    # print("JSON文件已保存至{}".format(file_path))


# insert 'template' item into juniper config model
def insert_template(config_model: dict) -> dict:
    for k, sub_dict in config_model.items():
        # 若子项不是 dict，可能是其他值，跳过（通常不应该出现，但做个保护）
        if not isinstance(sub_dict, dict):
            continue

        # 拿到该节点的 template，作为新 key
        template_key = sub_dict.get("template")
        if not template_key:
            # 没有 template 就插入
            sub_dict["template"] = k

        for child_k, child_v in sub_dict.items():
            insert_template({child_k: child_v})

    return config_model



if __name__ == "__main__":
    ''' # 最全面数据
        vendors = ['Cisco', "HUAWEI", "Juniper"]
        train_dataset_dirs = ['experiment/test_dataset/test_data_400',
                              'experiment/test_dataset/test_data_1200',
                              'experiment/test_dataset/test_data_2000',
                              'experiment/test_dataset/test_data_2800']

        project_root = Path(__file__).parent.parent

        for vendor in vendors:
            template_used_statistic = {}
            vendor_model = {}
            vendor_command_re = {}
            merge_count = 0
            for train_dataset_dir in train_dataset_dirs:
                folder_path = str(project_root / train_dataset_dir / f'Json_simplified/{vendor}')
                file_names_path = str(project_root / train_dataset_dir / f'command_tree/Cisco')   # 只用测试集试试效果
                json_files = get_json_filenames(file_names_path)
                for json_file in tqdm(json_files, desc=f"{vendor} {train_dataset_dir} Merged config num"):
                    json_config_path = folder_path + '/' + json_file
                    try:
                        json_config = load_json_file(json_config_path)
                    except:
                        continue
                    # 对vendor_model中的模版进行去重，主要问题是同样的conmand，llm在解析时可能出现不同的模版（配置参数缺失了），建议均采用最大的配置参数，我们需要一个字典来记录是否去重
                    vendor_model = merge_models(vendor_model, json_config, vendor_command_re, template_used_statistic)
            vendor_model_dir = str(project_root / f'dataset_multi_vendor_config/config_model/verified_data')
            os.makedirs(vendor_model_dir, exist_ok=True)
            save_json_file(vendor_model, f"{vendor_model_dir}/{vendor}.json")'''

    # 不同规模
    vendors = ['Cisco', "HUAWEI", "Juniper"]
    train_dataset_dir = 'experiment/test_dataset/all_data'
    name = 'all_data_2000'
    project_root = Path(__file__).parent.parent
    vendor_model_dir = str(project_root / f'dataset_multi_vendor_config/config_model/{name}')
    os.makedirs(vendor_model_dir, exist_ok=True)
    # for scale in [40, 80, 120]:
    for vendor in vendors:
        template_used_statistic = {}
        vendor_model = {}
        vendor_command_re = {}
        merge_count = 0
        folder_path = str(project_root / train_dataset_dir / f'Json_simplified/{vendor}')
        file_names_path = str(project_root / train_dataset_dir / f'command_tree/Cisco')
        json_files = get_json_filenames(file_names_path)
        for json_file in tqdm(json_files, desc=f"{vendor} {train_dataset_dir} Merged config num"):
            json_config_path = folder_path + '/' + json_file
            try:
                json_config = load_json_file(json_config_path)
            except:
                continue
            # 对vendor_model中的模版进行去重，主要问题是同样的conmand，llm在解析时可能出现不同的模版（配置参数缺失了），建议均采用最大的配置参数，我们需要一个字典来记录是否去重
            vendor_model = merge_models(vendor_model, json_config, vendor_command_re, template_used_statistic)
        save_json_file(vendor_model, f"{vendor_model_dir}/{vendor}.json")





