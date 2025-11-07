# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/17 16:48
@Auth ： xiaolongtuan
@File ：translate_explanation.py
"""
import json
from tqdm import tqdm
import requests
# 生成盐值和签名
import random
import hashlib

# 你的百度翻译API密钥
APP_ID = '20240302001979765'
SECRET_KEY = '2A83a1MpmgGXq_1Ny1Cf'

# 翻译请求的URL
url = "https://api.fanyi.baidu.com/api/trans/vip/translate"

def translate_Zh2Eng(text_to_translate):
    # 构造请求参数
    params = {
        'q': text_to_translate.encode('utf-8'),
        'from': 'zh',
        'to': 'en',
        'appid': APP_ID,
        'salt': '随机数',
        'sign': '签名'
    }

    salt = str(random.randint(1, 65536))
    sign_str = APP_ID + text_to_translate + salt + SECRET_KEY
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    params['salt'] = salt
    params['sign'] = sign

    response = requests.get(url, params=params)

    if response.status_code == 200:
        translation = response.json()
        if translation['trans_result']:
            # print('翻译结果:', translation['trans_result'][0]['dst'])
            trans_res = ""
            for seg in translation['trans_result']:
                trans_res += seg['dst']
            return trans_res
        else:
            # print('翻译失败:', translation['error_code'], translation['error_msg'])
            return '翻译失败:' + translation['error_code'], translation['error_msg']
    else:
        # print('请求失败，状态码:', response.status_code)
        return '请求失败，状态码:'+ response.status_code

def translated_rule_explanation(obj):
    if isinstance(obj, dict):
        if "explanation" in obj:
            obj['explanation'] = translate_Zh2Eng(obj['explanation'])

        for key, value in obj.items():
            translated_rule_explanation(value)
    elif isinstance(obj, list):
        for item in obj:
            translated_rule_explanation(item)

def update_by_2000_model(model, model_2000):
    updated_model = {}
    for k, v in model.items():
        if k not in model_2000:
            continue
        if isinstance(v, dict):
            updated_model[k] = update_by_2000_model(v, model_2000[k])
        else:
            updated_model[k] = model_2000[k]
    return updated_model

directory = "./different_scale_zh"
for vendor in tqdm(['Cisco', 'HUAWEI', 'Juniper']):
    file_path = f"./different_scale_zh/{vendor}_2000.json"
    with open(file_path, "r", encoding="utf-8") as f:
        model_2000 = json.load(f)
    translated_rule_explanation(model_2000)
    with open(f"./different_scale/{vendor}_2000.json", "w", encoding="utf-8") as f:
        json.dump(model_2000, f, ensure_ascii=False, indent=4)
    print(f"trslated {vendor}_2000.json")

    for scale in [100, 500, 1000]:
        file_path_2 = f"./different_scale_zh/{vendor}_{scale}.json"
        with open(file_path_2, "r", encoding="utf-8") as f:
            model = json.load(f)
        updated_model = update_by_2000_model(model, model_2000)
        with open(f"./different_scale/{vendor}_{scale}.json", "w", encoding="utf-8") as f:
            json.dump(updated_model, f, ensure_ascii=False, indent=4)
        print(f"updated {vendor}_{scale}.json")

