'''
从llm输出的txt文本中提取json，并最终合并为一个config解析后的json字典，如果在调用llm时直接使用json_outpurt，则不需要此步骤
'''
import re
import json
from pathlib import Path
import os


def get_txt_filenames(folder_path):
    folder = Path(folder_path)
    txt_filenames = [str(file.name) for file in folder.rglob('*.txt')]
    return txt_filenames


def load_config(file_path, file_name):
    with open(file_path + '/' + file_name, 'r', encoding='utf-8') as file:
        config = file.readlines()  # 逐行读取，存入列表
    # 拼接回字符串
    config = ''.join(config)
    return str(config)


def extract_longest_json(text):
    """
    从文本中提取所有用三重反引号包裹的 JSON 文本，
    返回其中字符数最长的 JSON 字符串（如果有多个则返回最长的一个）。
    """
    # 使用正则表达式提取 markdown 代码块内的内容
    # (?:json)? 表示可选的 "json" 标记，re.DOTALL 使 . 匹配换行符
    # pattern = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
    pattern = re.compile(r'```json\s*(\{.*?\})\s*```', re.DOTALL)
    # print(type(text), len(text))
    json_candidates = pattern.findall(text)

    if not json_candidates:
        return None  # 未找到 JSON 文本

    # 选择最长的那个 JSON 文本
    longest_json = max(json_candidates, key=len)
    return longest_json


def extract_json_config(text_data, save_path, txt_file):
    # 提取最长的 JSON 文本
    json_str = extract_longest_json(text_data)
    # print(json_str)
    if json_str is None:
        print("未找到 JSON 文本。")
        return

    # 尝试将提取出的 JSON 文本解析为 Python 对象
    try:
        json_obj = json.loads(json_str)
    except json.JSONDecodeError as e:
        print("提取的 JSON 无法解析:", e)
        return

    # 将 JSON 对象写入到 output.json 文件中
    name, _ = os.path.splitext(txt_file)
    output_filename = save_path + '/' + name + '.json'
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(json_obj, f, ensure_ascii=False, indent=4)

    print(f"成功提取最长的 JSON 文本，并保存到文件 {output_filename}")


if __name__ == "__main__":
    ## 加载文本
    vendors = ["Cisco", "HUAWEI", "Juniper"]
    for vendor in vendors:
        parsed_config_path = 'config_trans/dataset_multi_vendor_config/parsed_config/{}'.format(vendor)  # 解析加载思科的配置
        save_path = 'config_trans/dataset_multi_vendor_config/Json_config/{}'.format(vendor)
        txt_files = get_txt_filenames(parsed_config_path)
        for txt_file in txt_files:
            print(parsed_config_path + '/' + txt_file)
            if type(txt_file) == None:
                continue
            text = load_config(parsed_config_path, txt_file)
            extract_json_config(text, save_path, txt_file)
