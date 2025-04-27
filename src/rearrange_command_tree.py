import os
import json
from tqdm import tqdm

def parse_config(config_str):
    '''
    将配置字符串按缩进层级解析成嵌套字典结构
    '''
    lines = config_str.strip().split('\n')
    lines = [line for line in lines if not line.strip().startswith(('#', '!', '*', '/*', '*/'))]
    if not lines:
        return {}

    root = {}
    stack = [(0, root)]  # (缩进级别, 当前字典)

    for line in lines:
        if not line.strip():
            continue

        # 计算缩进级别
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        # 弹出所有大于当前缩进级别的节点
        while stack and stack[-1][0] >= indent:
            stack.pop()

        # 如果栈为空，说明第一行有缩进，直接添加到根节点
        if not stack:
            root[content] = {}
            stack.append((indent, root[content]))
            continue

        # 获取父节点
        parent_indent, parent_dict = stack[-1]

        # 添加当前节点
        parent_dict[content] = {}

        # 将当前节点压入栈
        stack.append((indent, parent_dict[content]))
    return root


def merge_tree_with_json(txt_tree, json_tree):
    """
    递归地将json_tree的属性填充到txt_tree的嵌套结构中。
    以txt_tree的结构为准，json_tree只用于补充属性。
    """
    result = {}
    for key, sub in txt_tree.items():
        node = {}
        # 只复制json_tree中与key同名的属性（如template、command、explanation、parameters等）
        if key in json_tree and isinstance(json_tree[key], dict):
            for attr in ["template", "command", "explanation", "parameters"]:
                if attr in json_tree[key]:
                    node[attr] = json_tree[key][attr]
        # 递归处理子节点
        if isinstance(sub, dict) and sub:
            node.update(merge_tree_with_json(sub, json_tree.get(key, {})))
        result[key] = node
    return result


def flatten_json_tree(json_tree):
    """
    将json_tree所有命令节点展平成{命令: 属性dict}的字典
    """
    flat = {}
    def _flatten(d):
        for k, v in d.items():
            if isinstance(v, dict):
                # 只保留属性字段
                flat[k] = {attr: v[attr] for attr in ["template", "command", "explanation", "parameters"] if attr in v}
                _flatten(v)
    _flatten(json_tree)
    return flat

def merge_tree_with_flat(txt_tree, flat_json):
    """
    以txt_tree结构为准，递归为每个命令节点复制flat_json中的属性
    """
    result = {}
    for key, sub in txt_tree.items():
        node = flat_json.get(key, {})
        if isinstance(sub, dict) and sub:
            node = {**node, **merge_tree_with_flat(sub, flat_json)}
        result[key] = node
    return result

def get_device_name_from_tree(tree, vendor):
    """
    从txt_tree或json_tree中提取设备名
    """
    if vendor == 'Cisco':
        for key in tree:
            if key.startswith('hostname '):
                return key.split(' ', 1)[1].strip()
    elif vendor == 'HUAWEI':
        for key in tree:
            if key.startswith('sysname '):
                return key.split(' ', 1)[1].strip()
    return None

def process_vendor(vendor):
    txt_dir = f"./experiment/train_dataset/text_config/{vendor}"
    json_dir = f"./experiment/train_dataset/command_tree/{vendor}"
    save_dir = f"./experiment/train_dataset_rearrange/command_tree/{vendor}"
    os.makedirs(save_dir, exist_ok=True)
    for filename in tqdm(os.listdir(txt_dir)):
        if not filename.endswith('.txt'):
            continue
        txt_path = os.path.join(txt_dir, filename)
        json_name = filename.replace('.txt', '.json')
        json_path = os.path.join(json_dir, json_name)
        save_path = os.path.join(save_dir, json_name)
        if not os.path.exists(json_path):
            continue
        # 读取txt
        with open(txt_path, 'r', encoding='utf-8') as f:
            txt_content = f.read()
        txt_tree = parse_config(txt_content)
        # 读取json
        with open(json_path, 'r', encoding='utf-8') as f:
            json_tree = json.load(f)
        # 判断设备名是否一致
        txt_dev = get_device_name_from_tree(txt_tree, vendor)
        json_dev = get_device_name_from_tree(json_tree, vendor)
        if txt_dev != json_dev:
            print(f"设备名不一致，跳过: {filename} (txt: {txt_dev}, json: {json_dev})")
            continue
        # 合并
        flat_json = flatten_json_tree(json_tree)
        new_tree = merge_tree_with_flat(txt_tree, flat_json)
        # 保存
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(new_tree, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    for vendor in ['Cisco', 'HUAWEI']:
        process_vendor(vendor)

