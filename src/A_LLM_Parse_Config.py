import json
import sys
import time
from pathlib import Path
import os
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_client(model_name:str, endpoint_url='https://api.deepseek.com/v1'):
    if 'gpt' in model_name:
        api_key = os.getenv("OPENAI_KEY")
    elif 'aliyun' in model_name:
        api_key = os.getenv("ALIYUN_API_KEY")
    elif 'deepseek' in model_name:
        api_key = os.getenv("DEEPSEEK_API_KEY")
    else:
        raise ValueError("Invalid model name")
    client = OpenAI(api_key = api_key, base_url=endpoint_url)
    return client

def get_txt_filenames(folder_path):
    folder = Path(folder_path)
    txt_filenames = [str(file.name) for file in folder.rglob('*.txt')]
    return txt_filenames

def load_config(file_path, file_name):
    with open(file_path + '/' + file_name, 'r', encoding='utf-8') as file:
        config = file.read()
    return config

def save_parsed_config(parsed_file_path, file_mane, parsed_config):
    if not os.path.exists(parsed_file_path):
        os.makedirs(parsed_file_path)
    with open(parsed_file_path + '/' + file_mane, 'w', encoding='utf-8') as file:
        json.dump(parsed_config, file)

def prompt_massage_for_vendors(vendor):
    project_root = Path(__file__).parent.parent

    system_prompt = "You are a helpful assistant specialized in network configuration analysis and transformation. Think step-by-step and provide detailed explanations."
    if vendor == 'Cisco':
        prompt_file = project_root / 'resource/Cisco_parse_config_prompt.txt'

        prompt = open(prompt_file, 'r', encoding='utf-8').read()
        massages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    elif vendor == 'HUAWEI':
        prompt_file = project_root / 'resource/HUAWEI_parse_config_prompt.txt'

        prompt = open(prompt_file, 'r', encoding='utf-8').read()
        massages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    elif vendor == 'Juniper':
        prompt_file = project_root / 'resource/Juniper_parse_config_prompt.txt'

        prompt = open(prompt_file, 'r', encoding='utf-8').read()
        massages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    return prompt, massages


def parse_config(client, model_name, prompt, messages, config_chunks:[]):
    config_parsed = {}
    for config_chunk in config_chunks:
        formatted_prompt = prompt.replace("{配置命令}", config_chunk)
        messages[1]["content"] = formatted_prompt

        max_retries = 2
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    response_format={
                        'type': 'json_object'
                    }
                )
                parsed_str = response.choices[0].message.content
                print(parsed_str)
                parsed_json = json.loads(parsed_str)
                config_parsed.update(parsed_json)
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    print(f"请求失败，已达到最大重试次数 {max_retries} 次。错误信息: {str(e)}")
                    return {"error": "请求失败"}
                time.sleep(2 ** retry_count)  # 指数退避
    return config_parsed

def process_file_service(config:str, vendor, client, model_name):
    prompt, messages = prompt_massage_for_vendors(vendor)
    response = str(parse_config(client, model_name, prompt, messages, config))
    return response # 作为一个输出指标

def splite_config(config, max_length=40):
    config_chunks = []
    current_chunk = []
    current_indent = 0

    for line in config.splitlines():
        if not line.strip():  # 跳过空行
            continue
        # 计算当前行的缩进级别
        indent = len(line) - len(line.lstrip())

        # 如果当前行是新的顶级命令（无缩进）且当前chunk已满
        if indent == 0 and len(current_chunk) >= max_length:
            config_chunks.append("\n".join(current_chunk))
            current_chunk = []

        # 如果当前行是子命令且与父命令不在同一个chunk中
        if indent > current_indent and len(current_chunk) >= max_length:
            # 找到最近的顶级命令（缩进为0）
            last_top_level = len(current_chunk) - 1
            while last_top_level >= 0 and len(current_chunk[last_top_level]) - len(
                    current_chunk[last_top_level].lstrip()) > 0:
                last_top_level -= 1

            # 将整个命令块移动到新的chunk
            config_chunks.append("\n".join(current_chunk[:last_top_level]))
            current_chunk = current_chunk[last_top_level:]

        current_chunk.append(line)
        current_indent = indent

    # 添加最后一个chunk
    if current_chunk:
        config_chunks.append("\n".join(current_chunk))

    return config_chunks


def process_file(config_file, full_config_path, save_path, vendor, client, model_name):
    # 检查目标文件是否已经存在
    output_file = os.path.join(save_path, config_file)
    if os.path.exists(output_file):
        return

    prompt, messages = prompt_massage_for_vendors(vendor)
    config = load_config(full_config_path, config_file)
    # 将较长的config分割为多个部分，每个部分的长度不超过40行
    config_chunks = splite_config(config, max_length=15)

    response = parse_config(client, model_name, prompt, messages, config_chunks)
    save_parsed_config(save_path, config_file, response)


if __name__ == "__main__":
    # model_name = "aliyun_deepseek-v3"
    # client = load_client(model_name, endpoint_url='https://dashscope.aliyuncs.com/compatible-mode/v1')

    model_name = "deepseek-chat"
    client = load_client(model_name)

    ## 配置加载
    if len(sys.argv) != 3:
        print("Usage: python 1LMM_Parse_Config.py <vendor> <config_path>")
        sys.exit(1)
    vendor = sys.argv[1]
    config_path = sys.argv[2]
    project_root = Path(__file__).parent.parent

    full_config_path =  str(project_root / 'dataset_multi_vendor_config/{}/{}'.format(config_path, vendor))
    ## 获取文件名
    txt_files = get_txt_filenames(full_config_path)
    print(txt_files[0])
    test_filenames = json.load(open( f'../syntactic_check/error_info/config_summary.json'))['all_config']['config']
    print(f"{len(test_filenames)}: {test_filenames[0]}")
    txt_files = [file for file in txt_files if file in test_filenames]
    print(len(txt_files))
    save_path = str(project_root / 'dataset_multi_vendor_config/Json_config/{}'.format(vendor))

    total_time = 0
    num_iterations = 1  # 测试次数
    start_time = time.time()
    num_threads = 8  # 设置线程数量

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # 过滤掉已处理的文件
        unprocessed_files = [
            f for f in txt_files
            if not os.path.exists(os.path.join(save_path, f))
        ]
        print(unprocessed_files)

        futures = [
            executor.submit(process_file, config_file, full_config_path, save_path, vendor, client, model_name)
            for config_file in unprocessed_files
        ]

        for future in tqdm(as_completed(futures), total=len(unprocessed_files)):
            iteration_start_time = time.time()
            future.result()
            iteration_end_time = time.time()
            iteration_time = iteration_end_time - iteration_start_time
            total_time += iteration_time

    end_time = time.time()
    total_elapsed_time = end_time - start_time
    average_time = total_time / num_iterations

    print(f"总耗时: {total_elapsed_time} 秒")
    print(f"平均每次循环耗时: {average_time} 秒")
