# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/20 12:16
@Auth ： xiaolongtuan
@File ：subdivision_juniper_json.py
"""
import os
import json
import re
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from tqdm import tqdm
from en_translator import translate_Zh2Eng

def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data

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
        self.executor = ThreadPoolExecutor(max_workers=5)  # 添加线程池

    def response(self, messages):
        def _request():
            for i in range(2):
                try:
                    response = self.llm_model.chat.completions.create(
                        model=self.model_name,
                        messages=messages
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    print(f"第 {i + 1} 次尝试失败，错误信息: {str(e)}")
            return ''

        return self.executor.submit(_request)

def split_parameters(text):
    pattern = re.compile(r'(\[parameter\d+\])|([^[\]]+)')
    segments = []
    current_text = ''
    current_params = []

    for match in pattern.finditer(text):
        if match.group(1):
            # 处理参数部分
            param = match.group(1)
            param_num = int(re.search(r'parameter(\d+)', param).group(1))
            current_params.append(param_num)
            current_text += param
        else:
            # 处理非参数部分
            non_param = match.group(2)
            if re.search(r'[^\s/]', non_param):
                if current_text or current_params:
                    segments.append({'text': current_text.strip(), 'params': current_params.copy()})
                    current_text = non_param
                    current_params = []
                else:
                    current_text += non_param
            else:
                current_text += non_param

    if current_text or current_params:
        segments.append({'text': current_text.strip(), 'params': current_params.copy()})

    # 提取结果和参数集合
    result_segments = [seg['text'] for seg in segments]
    param_sets = [seg['params'] for seg in segments]
    return result_segments, param_sets

'''
原来的思路是照着已经生成的模型进行拆分，但是一些之前没见过的命令依旧没有被拆分，所以这里我们还要调用segment
'''
def subdivision_config(llm_model:LLM_Model,old_config_model:dict, decompose_commands:dict, juniper_model:dict):
    tasks = []  # 用于收集所有需要处理的explanation任务
    node_refs = []  # 用于存储对应的节点引用

    new_config = {}
    for command, detail in old_config_model.items():
        command_words = command.split()
        command_temp = detail["template"]
        sub_model = new_config

        if command_temp in decompose_commands: # 使用已有的成果，不需要翻译
            seg = decompose_commands[command_temp]
            segments = seg[0]
            paras = seg[1]
            begin = 0
            command_node = juniper_model
            for k_part in range(len(segments)):
                segment = segments[k_part]
                segment_words = segment.split()
                command_match = ' '.join(command_words[begin:begin+len(segment_words)])
                command_node = command_node[segment]
                if command_match not in sub_model:
                    sub_model[command_match] = {"template": segment,
                                          "command": command_match,
                                          "explanation": command_node['explanation'],
                                          "parameters": command_node['parameters']}
                sub_model = sub_model[command_match]
                begin += len(segment_words)

        else:
            segments, paras = split_parameters(command_temp)
            command_node = juniper_model
            begin = 0
            for k_part in range(len(segments)):
                if len(segments) == 1:# 直接翻译原始的命令及解释
                    node = {"template": command_temp,
                                                "command": command,
                                                "explanation": translate_Zh2Eng(detail['explanation']),
                                                "parameters": detail['parameters']}
                    sub_model[command] = node
                    for param_node in node['parameters']:
                        param_node['explanation'] = translate_Zh2Eng(param_node['explanation'])
                    break

                segment = segments[k_part]
                segment_words = segment.split()
                command_match = ' '.join(command_words[begin:begin + len(segment_words)])
                if command_match not in sub_model: # 添加新的命令
                    if segment in command_node:  # 不需要翻译
                        command_node = command_node[segment]
                        sub_model[command_match] = {"template": segment,
                                                    "command": command_match,
                                                    "explanation": command_node['explanation'],
                                                    "parameters": command_node['parameters']}
                    else:# 没有当前命令的解释，使用llm直接输出英文，并翻译参数名
                        try:
                            node = {"template": segment,
                                                  "command": command_match,
                                                  "explanation": "",
                                                  "parameters": [detail['parameters'][i - 1] for i in paras[k_part]]}
                        except Exception as e:
                            print(f"error parameters paresed!")
                            continue
                        sub_model[command_match] = node
                        command_messges = [
                            {
                                "role": "user",
                                "content": f"You are a professional network engineer, please explain what this Junos command fragment does, directly answer the command explanation, the explanation is no longer than 30 words, the command is: {segment}"
                            }
                        ]
                        node_refs.append(node)
                        tasks.append(llm_model.response(command_messges))

                        for param_node in node['parameters']:
                            param_node['explanation'] = translate_Zh2Eng(param_node['explanation'])
                sub_model = sub_model[command_match]
                begin += len(segment_words)
    return tasks, node_refs, new_config

def process_juniper_json(json_config):
    processed_json = {}
    for k, v in json_config.items(): # 去除掉第一层 set xxx 命令
        if isinstance(v, dict):
            for command, info in v.items():
                processed_json[command] = info
    return processed_json

if __name__ == '__main__':
    '''
    将原始json command json转换为command tree
    '''
    juniper_model = load_json_file('../dataset_multi_vendor_config/config_model/scale388en/Juniper_388.json')
    decompose_command_path = "../dataset_multi_vendor_config/config_command_node/commands/decompose_Juniper_commands.json"
    decompose_commands = load_json_file(decompose_command_path)
    translation_llm = LLM_Model('aliyun_deepseek-v3', endpoint_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    source_dir = '../experiment/test_dataset/command_tree/Juniper'
    save_dir = '../experiment/test_dataset/command_tree/Juniper_subdivided'
    os.makedirs(save_dir, exist_ok=True)
    for filename in os.listdir(source_dir):
        if filename.endswith('.json'):
            save_path = os.path.join(save_dir, filename)
            if os.path.exists(save_path):
                continue
            file_path = os.path.join(source_dir, filename)
            old_config = load_json_file(file_path)
            old_config = process_juniper_json(old_config)

            if not old_config:
                continue

            # 使用相同的细分规则处理每个配置文件
            tasks, node_refs, subdivision_model = subdivision_config(translation_llm, old_config, decompose_commands, juniper_model)
            for future, node in tqdm(zip(tasks, node_refs), total=len(tasks), desc="处理解释任务"):
                node['explanation'] = future.result()

            # 保存细分后的配置文件
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(subdivision_model, f, ensure_ascii=False, indent=4)
