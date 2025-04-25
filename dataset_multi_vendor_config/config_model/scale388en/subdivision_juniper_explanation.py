# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/19 23:28
@Auth ： xiaolongtuan
@File ：subdivision_juniper_explanation.py
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from tqdm import tqdm


class Translation_Model:
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


def fill_explanations_recursive(llm_model: Translation_Model, node, parent_commands=None, old_config_model=None):
    if parent_commands is None:
        parent_commands = []

    tasks = []  # 用于收集所有需要处理的explanation任务
    node_refs = []  # 用于存储对应的节点引用

    if isinstance(node, dict):
        if 'explanation' in node and not node['explanation']:
            context = " ".join(parent_commands + [node['template']])
            if context in old_config_model:
                node['explanation'] = old_config_model[context]['explanation']
            else:
                messages = [
                    {"role": "system",
                     "content": "You are a professional network engineer, please explain what this Junos command fragment does, directly answer the command explanation, the explanation is no longer than 30 words"},
                    {
                        "role": "system",
                        "content": context
                    }
                ]
                # 收集任务和节点引用
                tasks.append(llm_model.response(messages))
                node_refs.append(node)

        # 递归处理子节点
        for key, value in node.items():
            if isinstance(value, dict):
                new_parent_commands = parent_commands.copy()
                if 'template' in node:
                    new_parent_commands.append(node['template'])
                child_tasks, child_refs = fill_explanations_recursive(llm_model, value, new_parent_commands, old_config_model)
                tasks.extend(child_tasks)
                node_refs.extend(child_refs)

    return tasks, node_refs


if __name__ == '__main__':
    with open('subdivision_Juniper_en.json', 'r') as file:
        subdivision_model = json.load(file)
    with open('old_Juniper_en.json', 'r') as file:
        old_config_model = json.load(file)
    translation_llm = Translation_Model('aliyun_deepseek-v3', endpoint_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    # 第一步：收集所有任务
    tasks, node_refs = fill_explanations_recursive(translation_llm, subdivision_model, None, old_config_model)

    # 第二步：并发执行所有任务
    for future, node in tqdm(zip(tasks, node_refs), total=len(tasks), desc="处理解释任务"):
        node['explanation'] = future.result()
    with open('new_Juniper_en.json', 'w') as file:
        json.dump(subdivision_model, file, indent=4)