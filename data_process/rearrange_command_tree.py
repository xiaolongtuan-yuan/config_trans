'''
处理我们在实验中使用到的数据集，根据config txt中的结构重新构建每个config对应的json解析
'''
import os
import json
import re
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from tqdm import tqdm

from src.C_Model_growth import placeholder_count


class LLM_Model:
    def __init__(self, model_name: str, endpoint_url: str = 'https://api.deepseek.com/v1'):
        if 'gpt' in model_name:
            api_key = os.getenv("OPENAI_KEY")
        elif 'aliyun' in model_name:
            api_key = os.getenv("ALIYUN_API_KEY")
            model_name = model_name.replace('aliyun_', '')
        elif 'deepseek' in model_name:
            api_key = os.getenv("DEEPSEEK_API_KEY")
        else:
            raise ValueError("Invalid model name")
        self.model_name = model_name
        self.llm_model = OpenAI(api_key=api_key, base_url=endpoint_url)
        self.executor = ThreadPoolExecutor(max_workers=10)  # 添加线程池

    def parse_command(self, command):
        messages = [
            {
                "role": "user",
                "content": open('../resource/command_parse_config_prompt.txt', 'r').read().replace('{command}', command),
            }
        ]
        def _request():
            for i in range(2):
                try:
                    response = self.llm_model.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        response_format={
                            'type': 'json_object'
                        }
                    )
                    parsed_command = json.loads(response.choices[0].message.content)
                    if not placeholder_count(parsed_command['template']) == len(parsed_command["parameters"]):
                        messages.append({"role": "user", "content": "注意template中参数占位符需要与parameters个数严格匹配"})
                        raise ValueError("占位符与参数不匹配")
                    return parsed_command
                except Exception as e:
                    print(f"第 {i + 1} 次尝试失败，错误信息: {str(e)}")
            return ''

        return self.executor.submit(_request)

def parse_config(config_str):
    '''
    将配置字符串按缩进层级解析成嵌套字典结构
    '''
    lines = config_str.strip().split('\n')
    lines = [line for line in lines if not line.strip().startswith(('#', '!', '*', '/*', '*/', '/'))]
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
def flatten_json_tree(json_tree):
    """
    将json_tree所有命令节点展平成{命令: 属性dict}的字典
    """
    flat = {}
    def _flatten(d):
        for k, v in d.items():
            if isinstance(v, dict):
                # 只保留属性字段
                try:
                    flat[k] = {attr: v[attr] for attr in ["template", "command", "explanation", "parameters"]}
                    _flatten(v)
                except Exception as e:
                    print(e)
                    _flatten(v)

    _flatten(json_tree)
    return flat

def merge_tree_with_flat(txt_tree, flat_json, filename):
    """
    以txt_tree结构为准，递归为每个命令节点复制flat_json中的属性,并翻译描述
    """
    tasks = []
    result = {}
    for key, sub in txt_tree.items():
        node = flat_json.get(key, {"command": key}).copy()
        if key not in flat_json:
            # print(f"{key} not in {filename} flat_json")
            future = llm_model.parse_command(key)
            node_ref = node
            tasks.append((future, node_ref))

        else:
            command = key
            template = node.get('template')
            params = para_extract(command, template)
            try:
                if len(params) != len(node.get('parameters')):
                    # 解析有问题，重新来
                    future = llm_model.parse_command(key)
                    node_ref = node
                    tasks.append((future, node_ref))
            except Exception as e:
                print(e)
                future = llm_model.parse_command(key)
                node_ref = node
                tasks.append((future, node_ref))

        if isinstance(sub, dict) and sub:
            sub_node, sub_tasks = merge_tree_with_flat(sub, flat_json, filename)
            node.update(sub_node)
            tasks.extend(sub_tasks)

        result[key] = node
    return result, tasks

def process_vendor(vendor):
    tasks = []
    # for condif_dir in ['400', '1200', '2000', '2800']:
    for condif_dir in ['1200', '2800']:
        txt_dir = f"../experiment/test_dataset/test_data_{condif_dir}/text_config/{vendor}"
        json_dir = f"../experiment/test_dataset/test_data_{condif_dir}/command_tree/{vendor}"
        save_dir = f"../experiment/test_dataset/test_data_{condif_dir}/command_tree/{vendor}"
        os.makedirs(save_dir, exist_ok=True)
        for filename in os.listdir(txt_dir):
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
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_tree = json.load(f)
            except Exception as e:
                raise Exception(e)
            flat_json = flatten_json_tree(json_tree)
            new_tree, merge_tasks = merge_tree_with_flat(txt_tree, flat_json, filename)
            tasks.append((save_path, new_tree, merge_tasks))
    for save_path, new_tree, merge_tasks in tqdm(tasks):
        for future, node_ref in merge_tasks:
            result = future.result()
            if result:
                node_ref.update(result)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(new_tree, f, ensure_ascii=False, indent=4)
    # 保存

def para_extract(cmd: str, template: str) -> str:
    # print(cmd, template)
    # 将源模板转换为正则表达式
    # 例如 "hostname [parameter1]" -> r"hostname (\S+)"
    if bool(re.search(r"\[[^\]]+\]", template)):
        src_regex = re.sub(r"\[[^\]]+\]", r"(\\S+)", template)
    else:
        src_regex = re.escape(template)
    # 匹配源命令并提取参数
    try:
        match = re.match(src_regex, cmd)
    except re.error:
        return []
    if not match:
        # raise ValueError(f"源命令 '{cmd}' 不匹配模板 '{template}'")
        return []
    # 提取参数
    parameters = match.groups()
    return parameters

if __name__ == '__main__':
    # 更新command tree

    llm_model = LLM_Model('deepseek-chat')
    for vendor in ['Cisco','HUAWEI','Juniper']:
        process_vendor(vendor)

