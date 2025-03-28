# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/14 20:50
@Auth ： xiaolongtuan
@File ：E_plus_match_examine.py
"""
import os
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm

'''
加载‘dataset_multi_vendor_config/mapping_template_library’下的映射文件，使用llm检查每一项映射是否存在错误，如果存在错误则修复
'''
import json
from concurrent.futures import ThreadPoolExecutor, as_completed


def load_client(model_name: str, endpoint_url: str):
    if 'gpt' in model_name:
        api_key = os.getenv("OPENAI_KEY")
    elif 'deepseek' in model_name:
        api_key = os.getenv("DEEPSEEK_API_KEY")
    else:
        raise ValueError("Invalid model name")
    client = OpenAI(api_key=api_key, base_url=endpoint_url)
    return client


def process_mapping_response(response):
    try:
        data = json.loads(response)

        if "errors" in data:
            print("发现以下问题：")
            for error in data["errors"]:
                print(f"- {error}")

            if "corrected_data" in data:
                return data["corrected_data"]
            else:
                print("未提供修正数据，保留原始映射")
                return None
        else:
            print("未发现错误，映射关系正确")
            return None

    except json.JSONDecodeError:
        print("返回数据格式错误")
        return None


def split_mapping_data(mapping_data, chunk_size=10):
    """
    将mapping_data字典划分为多个大小为chunk_size的小字典
    """
    items = list(mapping_data.items())
    chunks = [dict(items[i:i + chunk_size]) for i in range(0, len(items), chunk_size)]
    return chunks


def merge_mapping_chunks(chunks, mapping_data, simple_templates):
    """
    将多个chunk合并为一个字典
    """
    merged_dict = {}
    llm_dict = {}
    for chunk_str in chunks:
        chunk = json.loads(chunk_str)
        llm_dict.update(chunk)

    for source_command, detail in llm_dict.items():
        old_detail = mapping_data[source_command]
        if not detail == old_detail:
            if isinstance(detail, list):
                try:
                    index = 0
                    for line in detail:
                        i, j, target_command = line[0], line[1], line[2]
                        if not i == index:
                            raise ValueError("index error")

                        index += 1
                        if target_command not in simple_templates:
                            continue
                        else:
                            old_detail[i] = [i, j, target_command]

                except Exception as e:
                    continue
            elif isinstance(detail, str):
                if detail not in simple_templates:
                    continue
                else:
                    mapping_data[source_command] = detail
            else:
                raise ValueError("detail type error")

    return mapping_data

'''
"ip address [parameter1] [parameter2]": [
    [
        0,
        0,
        "ip address [parameter1] [parameter2]"
    ],
    [
        1,
        1,
        "ip address [parameter1] [parameter2]"
    ]
]
'''


def chunk_llm_check(client, model_name, prompt, chunk):
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": str(chunk)}
            ]
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={
                    'type': 'json_object'
                }
            )
            new_match_chunk = response.choices[0].message.content
            return new_match_chunk
        except Exception as e:
            retry_count += 1
            print(f"第 {retry_count} 次尝试失败，错误信息: {str(e)}")
            if retry_count == max_retries:
                print("已达到最大重试次数，放弃处理")
                return chunk
            print("准备重试...")


def llm_check_mapping(client, model_name, mapping_data, source_vendor, target_vendor, prompt_path, simple_templates):
    '''
    使用llm检查每一项映射是否存在错误，如果存在错误则修复
    '''
    prompt = open(prompt_path, 'r', encoding='utf-8').read()
    prompt = prompt.replace("{src_vendor}", source_vendor)
    prompt = prompt.replace("{target_vendor}", target_vendor)

    mapping_chunks = split_mapping_data(mapping_data, chunk_size=10)

    new_match_chunks = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(chunk_llm_check, client, model_name, prompt, chunk): chunk for chunk in
                   mapping_chunks}

        for future in tqdm(as_completed(futures), total=len(mapping_chunks), desc="处理映射"):
            try:
                new_match_chunk = future.result()

                new_match_chunks.append(new_match_chunk)
            except Exception as e:
                print(f"处理映射块时发生错误: {e}")
    # 保存new_match_chunks
    with open(f'./temp_{source_vendor}_{target_vendor}_data.json', 'w', encoding='utf-8') as f:
        json.dump(new_match_chunks, f, ensure_ascii=False, indent=4)
    new_mapping = merge_mapping_chunks(new_match_chunks, mapping_data, simple_templates)
    return new_mapping


if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    mapping_library_path = project_root / 'dataset_multi_vendor_config' / 'mapping_template_library' / 'different_scale'
    config_num = [100, 500, 1000]

    simple_templates_dir = project_root / 'dataset_multi_vendor_config/config_command_node_debug/different_scale'
    vendors = ["Cisco", "HUAWEI", "Juniper"]
    prompt_path = project_root / "resource" / "match_examine_prompt.txt"
    model_name = "deepseek-chat"
    client = load_client(model_name, endpoint_url='https://api.deepseek.com/v1')

    for scale in config_num:
        for source_vendor in vendors:
            for target_vendor in vendors:
                if source_vendor == target_vendor:
                    continue
                if f"{target_vendor}_{scale}.json" == 'Cisco_HUAWEI_100.json':
                    continue
                mapping_file_path = mapping_library_path / f"{source_vendor}_{target_vendor}_{scale}.json"

                simple_templates_path = simple_templates_dir / f"{target_vendor}_{scale}.json"
                with open(simple_templates_path, 'r', encoding='utf-8') as f:
                    simple_templates = json.load(f)

                with open(mapping_file_path, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)

                response = llm_check_mapping(client, model_name, mapping_data, source_vendor, target_vendor, prompt_path,
                                     simple_templates)
                # 保存response
                save_path = project_root / 'dataset_multi_vendor_config' / 'mapping_template_library_examined' / 'different_scale'
                save_path.mkdir(parents=True, exist_ok=True)
                save_file = f"{source_vendor}_{target_vendor}_{scale}.json"
                save_file_path = save_path / save_file
                with open(save_file_path, 'w', encoding='utf-8') as f:
                    json.dump(response, f, ensure_ascii=False, indent=4)
                print(f"处理完成scale{scale}: {source_vendor}到{target_vendor}的映射")

