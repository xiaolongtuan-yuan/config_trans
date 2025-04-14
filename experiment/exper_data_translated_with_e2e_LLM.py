# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:46
@Auth ： xiaolongtuan
@File ：exper_data_translated.py
"""
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
import os
import json
from tqdm import tqdm  # 用于显示进度条


class E2E_Config_Translater:
    def __init__(self, model_name: str):
        if 'gpt' in model_name:
            api_key = os.getenv("OPENAI_KEY")
            endpoint_url = 'https://api.openai.com/v1'

        elif 'deepseek' in model_name:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            endpoint_url = 'https://api.deepseek.com/v1'
        else:
            raise ValueError("Invalid model name")
        self.model_name = model_name
        self.llm_model = OpenAI(api_key=api_key, base_url=endpoint_url)
        self.translate_prompt = open('../resource/e2e_llm_translate_prompt.txt', 'r', encoding='utf-8').read()

    def translation(self, source_config: str, source_vendor: str, target_vendor: str) -> str:
        prompt = self.translate_prompt.replace("{source_config}", source_config)
        prompt = prompt.replace("{source_vendor}", source_vendor)
        prompt = prompt.replace("{target_vendor}", target_vendor)

        messages = [
            {"role": "user", "content": prompt}
        ]
        for i in range(3):
            try:
                response = self.llm_model.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={
                        'type': 'json_object'
                    }
                )
                json_response = response.choices[0].message.content
                json_response = json.loads(json_response)
                return json_response.get('translated_config', '')
            except Exception as e:
                print(f"第 {i + 1} 次尝试失败，错误信息: {str(e)}")
        return ''


def batch_translate(config_translater, input_dir, txt_file_dir, output_dir, source_vendor, target_vendor,
                    batch_size=100):
    # 获取所有配置文件
    config_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]

    # 创建输出目录
    os.makedirs(os.path.join(output_dir, target_vendor), exist_ok=True)

    # 遍历每个文件进行翻译
    successed_files = 0

    with ThreadPoolExecutor() as executor:  # 多线程好像有点问题，暂时不使用
        futures = []
        for file_index in range(batch_size):
            config_file = config_files.pop(0)
            futures.append(executor.submit(translate_single_file,
                                           config_translater, txt_file_dir, output_dir,
                                           source_vendor, target_vendor, config_file))
        with tqdm(total=batch_size, desc="Successed files") as pbar:
            i = 0
            while i < len(futures):
                future = futures[i]
                try:
                    if future.result():
                        successed_files += 1
                        pbar.update(1)
                except Exception as e:
                    print(f"\nError: {str(e)}")
                    if config_files:
                        config_file = config_files.pop(0)
                        futures.append(executor.submit(translate_single_file,
                                                       config_translater, txt_file_dir, output_dir,
                                                       source_vendor, target_vendor, config_file))
                i+=1

        print(f"Translated {successed_files} configs")

def preprocess_text(text):
    # 去除注释（以#或!开头的行）
    lines = [line for line in text.splitlines() if not line.strip().startswith(('#', '!'))]
    # 去除中文词汇（保留ASCII字符）
    cleaned_text = ''.join(char for char in '\n'.join(lines) if ord(char) < 128)
    return cleaned_text

def translate_single_file(config_translater: E2E_Config_Translater, txt_file_dir, output_dir,
                          source_vendor, target_vendor, config_file):
    try:
        # 加载配置
        file_name = os.path.splitext(config_file)[0]
        config_path = os.path.join(txt_file_dir, file_name+'.txt')

        source_config = open(config_path, 'r', encoding='utf-8').read()

        source_config = preprocess_text(source_config)

        # 翻译到目标供应商
        output_path = os.path.join(output_dir, target_vendor, f"{file_name}.txt")
        trans_res = config_translater.translation(source_config, source_vendor, target_vendor)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(trans_res)
        return True
    except Exception as e:
        print(f"\nError translating {config_file}: {str(e)}")
        return False


def delete_outdate_files(file_dir):
    os.makedirs(file_dir, exist_ok=True)
    # 清空目录下的所有文件
    for file in os.listdir(file_dir):
        file_path = os.path.join(file_dir, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")


def main():
    # 初始化路径
    output_dir = './exper_data/e2e_llm_translated_config'

    vendors = ["Cisco", "HUAWEI", "Juniper"]
    llm_models = ["deepseek-chat", "gpt-4o-mini"]
    for llm_model in llm_models:
        for source_vendor in vendors:
            for target_vendor in vendors:
                if source_vendor == target_vendor:
                    continue
                source_config_dir = f'./exper_data/{source_vendor}'
                txt_file_dir = f'./exper_data/lable/{source_vendor}'
                output_save_dir = os.path.join(output_dir, llm_model, source_vendor)  # 当前处理的是哪个scale的哪个源供应商
                os.makedirs(output_save_dir, exist_ok=True)
                delete_outdate_files(os.path.join(output_dir, llm_model, source_vendor, target_vendor))

                print(f"exper for {llm_model}, from {source_vendor} to {target_vendor} translation")

                config_translater = E2E_Config_Translater(llm_model)

                # 执行批量翻译
                batch_translate(config_translater=config_translater,
                                input_dir=source_config_dir,
                                txt_file_dir=txt_file_dir,
                                output_dir=output_save_dir,
                                source_vendor=source_vendor,
                                target_vendor=target_vendor,
                                batch_size=50)


if __name__ == "__main__":
    main()
