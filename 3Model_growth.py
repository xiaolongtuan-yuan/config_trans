import json
import argparse
import glob
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
            existing_node[key] = val
        else:
            # 若都为 dict，则需要递归合并，否则跳过（只保留第一次）
            if isinstance(existing_node[key], dict) and isinstance(val, dict):
                merge_nodes(existing_node[key], val)
            # 其余情况按照“保留第一次出现”的原则，不覆盖 existing_node[key]
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


def merge_models(config1, config2):
    """
    递归地将 config2 中不存在于 config1 的节点合并到 config1 中。
    如果 key 存在于 config1 且对应子节点都是字典，则继续合并其子节点；
    如果 key 不存在于 config1，则将 config2[key] 直接插入到 config1；
    如果 key 都存在，但对应的值不是字典，则保持 config1 原值不变（即不覆盖）。
    """
    for key, value in config2.items():
        if key not in config1:
            # 如果 config1 中没有该键，直接插入
            config1[key] = value
        else:
            # 如果 config1 中已经存在这个 key，
            # 且双方都是 dict，则递归合并子节点
            if isinstance(value, dict) and isinstance(config1[key], dict):
                merge_models(config1[key], value)
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
            insert_template({child_k:child_v})

    return config_model

def delete_all_json_files(folder_path):
    # 使用glob模块找到文件夹中所有的.json文件
    json_files = glob.glob(os.path.join(folder_path, "*.json"))

    # 遍历所有找到的.json文件并删除
    for json_file in json_files:
        try:
            os.remove(json_file)
            print(f"已删除文件: {json_file}")
        except Exception as e:
            print(f"删除文件 {json_file} 时出错: {e}")


if __name__ == "__main__":
    '''
    parser = argparse.ArgumentParser(description="配置模型解析合并")
    parser.add_argument("--vendor", required=True, help="vendor")
    args = parser.parse_args()

    vendor = args.vendor

     # Example Input
    file_path1 = 'test_data/{}/config1_parsed.json'.format(vendor)
    file_path2 = 'test_data/{}/config2_parsed.json'.format(vendor)
    config1_parsed = load_json_file(file_path1)
    config2_parsed = load_json_file(file_path2)

    if vendor == "juniper":
        config1_parsed = insert_template(config1_parsed)
        config2_parsed = insert_template(config2_parsed)

    print(json.dumps(config1_parsed, indent=4, ensure_ascii=False))
    print(json.dumps(config1_parsed, indent=4, ensure_ascii=False))

    # Simplify the input data
    config1_simplified = simplify_json(config1_parsed)
    config2_simplified = simplify_json(config2_parsed)
    # Save the output data
    model_path1 = 'test_data/{}/config1_simplified.json'.format(vendor)
    model_path2 = 'test_data/{}/config2_simplified.json'.format(vendor)
    save_json_file(config1_simplified, model_path1)
    save_json_file(config2_simplified, model_path2)

    # Print the result
    print(json.dumps(config1_simplified, indent=4, ensure_ascii=False))
    print(json.dumps(config2_simplified, indent=4, ensure_ascii=False))

    growth_model = merge_models(config1_simplified, config2_simplified)
    print(json.dumps(growth_model, indent=4, ensure_ascii=False))
    growth_model_path = 'test_data/{}_growth_model.json'.format(vendor)
    save_json_file(growth_model, growth_model_path)
    '''

    vendors = ["Cisco", "HUAWEI", "Juniper"]
    '''
    for vendor in vendors:
        folder_path = 'config_trans/dataset_multi_vendor_config/Json_config/{}'.format(vendor)
        json_files = get_json_filenames(folder_path)
        # 删除指定文件夹中的所有.json文件
        delete_all_json_files(folder_path)
    '''

    # simplify the device configuration model
    '''for vendor in vendors:
        folder_path = 'config_trans/dataset_multi_vendor_config/Json_config/{}'.format(vendor)
        save_path = 'config_trans/dataset_multi_vendor_config/Json_config/{}'.format(vendor+'_simplified')
        json_files = get_json_filenames(folder_path)
        for json_file in json_files:
            json_config_path = folder_path + '/' + json_file
            json_config = load_json_file(json_config_path)
            if vendor == 'Juniper':
                # Juniper配置层级多, 与huawei, cisco一致的化简流程会出错, 插入template保持一致
                json_config = insert_template(json_config)
            json_config_simplified = simplify_json(json_config)
            json_name, _ = os.path.splitext(json_file)
            save_file_path = save_path + '/' + json_name + '.json'
            save_json_file(json_config_simplified, save_file_path)'''

    # merge the device configuration to the vendor model
    for vendor in vendors:
        folder_path = 'config_trans/dataset_multi_vendor_config/Json_config/{}_simplified'.format(vendor)
        vendor_model_path = 'config_trans/dataset_multi_vendor_config/config_model/{}.json'.format(vendor)
        json_files = get_json_filenames(folder_path)
        merge_count = 0
        for json_file in tqdm(json_files, desc="Merged config num"):
            json_config_path = folder_path + '/' + json_file
            print(json_config_path)
            # 加载设备配置模型
            json_config = load_json_file(json_config_path)
            # 加载供应商配置模型
            vendor_model = load_json_file(vendor_model_path)
            vendor_model = merge_models(vendor_model, json_config)
            save_json_file(vendor_model, vendor_model_path)
            merge_count += 1
        print(merge_count)


   