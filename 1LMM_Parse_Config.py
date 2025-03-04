import sys
import time
from pathlib import Path
import os
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_client(model_name:str, endpoint_url:str):
    if 'gpt' in model_name:
        api_key = os.getenv("OPENAI_KEY")
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
        file.write(parsed_config)

def prompt_massage_for_vendors(vendor):
    system_prompt = "You are a helpful assistant specialized in network configuration analysis and transformation. Think step-by-step and provide detailed explanations."
    if vendor == 'Cisco':
        prompt = open('resource/Cisco_parse_config_prompt.txt', 'r', encoding='utf-8').read()
        massages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    elif vendor == 'HUAWEI':
        prompt = open('resource/HUAWEI_parse_config_prompt.txt', 'r', encoding='utf-8').read()
        massages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    elif vendor == 'Juniper':
        prompt = open('resource/Juniper_parse_config_prompt.txt', 'r', encoding='utf-8').read()
        massages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    return prompt, massages


def parse_config(client, model_name, prompt, messages, config):
    formatted_prompt = prompt.replace("{配置命令}", config)
    messages[1]["content"] = formatted_prompt

    max_retries = 3
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
            new_text = response.choices[0].message.content
            return new_text
        except Exception as e:
            retry_count += 1
            if retry_count == max_retries:
                print(f"请求失败，已达到最大重试次数 {max_retries} 次。错误信息: {str(e)}")
                return '{"error": "请求失败"}'
            time.sleep(2 ** retry_count)  # 指数退避
    return None


def process_file(config_file, full_config_path, save_path, vendor, client, model_name):
    # 检查目标文件是否已经存在
    output_file = os.path.join(save_path, config_file)
    if os.path.exists(output_file):
        return

    prompt, messages = prompt_massage_for_vendors(vendor)
    config = load_config(full_config_path, config_file)
    response = parse_config(client, model_name, prompt, messages, config)
    save_parsed_config(save_path, config_file, response)



if __name__ == "__main__":
    model_name = "deepseek-chat"
    client = load_client(model_name, endpoint_url='https://api.deepseek.com/v1')
    ## 配置加载
    if len(sys.argv) != 3:
        print("Usage: python 1LMM_Parse_Config.py <vendor> <config_path>")
        sys.exit(1)
    vendor = sys.argv[1]
    config_path = sys.argv[2]

    full_config_path =  'dataset_multi_vendor_config/{}/{}'.format(config_path, vendor)
    ## 获取文件名
    txt_files = get_txt_filenames(full_config_path)
    save_path = 'dataset_multi_vendor_config/Json_config/{}'.format(vendor)

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
