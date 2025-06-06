'''
对json文件中国的每个节点进行简化和检查，并将命令模版作为节点的键值
'''
import json
from pathlib import Path
import os
from tqdm import tqdm


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
            '''filtered_val = filter_valid_nodes(val)
            if filtered_val:
                existing_node[key] = filtered_val'''
            existing_node[key] = val
        else:
            # 若都为 dict，则需要递归合并，否则跳过（只保留第一次）
            if isinstance(existing_node[key], dict) and isinstance(val, dict):
                merge_nodes(existing_node[key], val)
            # 其余情况按照"保留第一次出现"的原则，不覆盖 existing_node[key]
    return existing_node


def simplify_json(input_dict: dict) -> dict:
    """
    遍历 input_dict，每个顶层 key 都有一个子 dict（里面有 "template"）。
    以 'template' 的值作为新 key 放入结果中，若重复则进行合并。
    对其子节点做相同处理，递归简化。
    """
    result = {}

    def _simplify(current_dict: dict) -> dict:
        """
        对当前字典的所有 (key -> sub_dict) 进行简化，
        返回一个按照 template 合并过后的子字典。
        """
        temp_result = {}
        for k, sub_dict in current_dict.items():
            # 若子项不是 dict，可能是其他值，跳过（通常不应该出现，但做个保护）
            # print('sub_dict:', json.dumps(sub_dict, indent=4, ensure_ascii=False))
            if not isinstance(sub_dict, dict):
                # print('不是字典-----------------')
                continue
            required_fields = ["template", "command", "explanation", "parameters"]
            if not all(field in sub_dict for field in required_fields):
                continue

            # 拿到该节点的 template，作为新 key
            template_key = sub_dict.get("template")
            if not template_key:
                # 没有 template 就跳过
                # print('没有template')
                continue

            # 先递归处理 sub_dict 的子节点
            # 子节点指的就是 sub_dict 里那些既是 key，又是一个 dict 的结构
            # 比如 "ip address 10.1.1.10 255.255.255.0" 这种
            child_dict = {}
            for child_k, child_v in sub_dict.items():
                # 判断是不是子节点（child_k 对应的值是 dict，并且里面有 template）
                if (
                        isinstance(child_v, dict)
                        and "template" in child_v
                ):
                    # 先递归处理子节点自身
                    # 再将其合并到 child_dict 中
                    simplified_sub = _simplify({child_k: child_v})
                    merge_nodes(child_dict, simplified_sub)
                else:
                    # 不是子节点，就先原样放进去
                    if child_k not in ("template",):
                        # "template" 字段不需要再放到 child_dict 的下一层
                        child_dict[child_k] = child_v

            # 整合成一个新的节点
            new_node = {
                "template": template_key
            }
            # child_dict 就是子节点合并后的结果，把它并回去
            merge_nodes(new_node, child_dict)

            # 把这个新节点合并到 temp_result 中
            if template_key not in temp_result:
                temp_result[template_key] = new_node
            else:
                # 如果 template_key 已经存在，需要合并
                merge_nodes(temp_result[template_key], new_node)

            # print('temp_result:', json.dumps(temp_result, indent=4, ensure_ascii=False))

        return temp_result

    # 整体处理 input_dict，得到结果
    # print('解析模型：', input_dict)
    result = _simplify(input_dict)
    return result


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


def check_juniper_config(config_model: dict) -> bool:
    '''
    juniper的配置中，所有的command应该都是以set xxx开头
    '''
    VALID_FIRST_WORDS = ['set', 'delete', 'rename', 'deactivate', 'activate', 'replace', 'commit']

    def _check_commands(node: dict):
        for key, value in node.items():
            if key == 'command':
                if not isinstance(value, str):
                    return False
                first_word = value.split()[0] if value else ''
                if first_word not in VALID_FIRST_WORDS:
                    print(value)
                    return False
            elif isinstance(value, dict):
                if not _check_commands(value):
                    return False
        return True

    return _check_commands(config_model)


def filter_valid_nodes(node: dict) -> dict:
    """
    递归过滤，只保留属性齐全（template、command、explanation、parameters）的节点。
    """
    if not isinstance(node, dict):
        return node
    required_fields = ["template", "command", "explanation", "parameters"]
    # 只保留属性齐全的节点
    if all(field in node for field in required_fields):
        filtered = {}
        for k, v in node.items():
            if isinstance(v, dict):
                child = filter_valid_nodes(v)
                if child and isinstance(child, dict) and all(field in child for field in required_fields):
                    filtered[k] = child
                elif not isinstance(v, dict):
                    filtered[k] = v
            else:
                filtered[k] = v
        return filtered
    else:
        return None


if __name__ == "__main__":
    vendors = ["Juniper", "Cisco", "HUAWEI"]
    train_dataset_dirs = ['experiment/test_dataset/test_data_2000']

    project_root = Path(__file__).parent.parent

    # simplify the device configuration model
    for vendor in vendors:
        for train_dataset_dir in train_dataset_dirs:
            if vendor == 'Juniper':
                folder_path = str(project_root / train_dataset_dir / 'command_tree' / '{}_subdivided'.format(vendor))
            else:
                folder_path = str(project_root / train_dataset_dir / 'command_tree' / '{}'.format(vendor))
            save_path = str(project_root / train_dataset_dir / 'Json_simplified/{}'.format(vendor))
            os.makedirs(save_path, exist_ok=True)
            json_files = get_json_filenames(folder_path)
            for json_file in tqdm(sorted(json_files), f'{vendor} {train_dataset_dir}'):
                json_config_path = folder_path + '/' + json_file
                json_config = load_json_file(json_config_path)
                json_config_simplified = simplify_json(json_config)
                json_name, _ = os.path.splitext(json_file)
                save_file_path = save_path + '/' + json_name + '.json'
                save_json_file(json_config_simplified, save_file_path)

'''    dic = {"no synchronization": {
            "template": "no synchronization",
            "command": "no synchronization",
            "explanation": "Disable BGP Sync",
            "parameters": []
        }}
    print(filter_valid_nodes(dic))'''
    