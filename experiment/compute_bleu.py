# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:30
@Auth ： xiaolongtuan
@File ：compute_bleu.py
"""
import os
from nltk.translate.bleu_score import sentence_bleu
import json

def preprocess_text(text):
    # 去除注释（以#或!开头的行）
    lines = [line for line in text.splitlines() if not line.strip().startswith(('#', '!'))]
    # 去除中文词汇（保留ASCII字符）
    cleaned_text = ''.join(char for char in ' '.join(lines) if ord(char) < 128)
    return cleaned_text.split()


def compute_bleu_for_configs(translated_dir, real_dir, config_files):
    total_bleu = 0.0
    count = 0
    for config_file in config_files:
        # 读取翻译后的配置文件
        with open(os.path.join(translated_dir, config_file), 'r') as f:
            translated_config = f.read()

        # 读取真实配置文件
        with open(os.path.join(real_dir, config_file), 'r') as f:
            real_config = f.read()

        # 将文本分割为单词列表
        translated_words = translated_config.split()
        real_words = preprocess_text(real_config)

        # 计算BLEU分数
        bleu_score = sentence_bleu([real_words], translated_words)
        total_bleu += bleu_score
        count += 1

    return total_bleu / count if count > 0 else 0.0

# 统计配置文件中的单词匹配率
def compute_word_match_rate(translated_dir, real_dir, config_files):
    total_word_count = 0
    matched_word_count = 0
    for config_file in config_files:
        # 读取翻译后的配置文件
        with open(os.path.join(translated_dir, config_file), 'r') as f:
            translated_config = f.read()
        # 读取真实配置文件
        with open(os.path.join(real_dir, config_file), 'r') as f:
            real_config = f.read()
        translated_words = translated_config.split()
        real_words = preprocess_text(real_config)

        total_word_count += len(translated_words)
        matched_word_count += sum(1 for word in translated_words if word in real_words)
    return matched_word_count / total_word_count if total_word_count > 0 else 0.0

cisco_huawei_config_dir = './exper_data/cisco_translated_config/HUAWEI'
# cisco_huawei_config_dir = './exper_data/cisco_translated_config_with_mapping_examined/HUAWEI'

cisco_to_huawei_config_files = [f for f in os.listdir(cisco_huawei_config_dir) if f.endswith('.txt')]
huawei_real_config_dir = './exper_data/HUAWEI'

cisco_juniper_config_dir = './exper_data/cisco_translated_config/Juniper'
cisco_to_juniper_config_files = [f for f in os.listdir(cisco_juniper_config_dir) if f.endswith('.txt')]
juniper_real_config_dir = './exper_data/Juniper'

# 计算Cisco到Huawei的BLEU分数
huawei_words = compute_word_match_rate(cisco_huawei_config_dir, huawei_real_config_dir, cisco_to_huawei_config_files)
print(f"Cisco to Huawei words accuracy score: {huawei_words}")

# # 计算Cisco到Juniper的BLEU分数
# juniper_bleu = compute_bleu_for_configs(cisco_juniper_config_dir, juniper_real_config_dir, cisco_to_juniper_config_files)
# print(f"Cisco to Juniper BLEU score: {juniper_bleu}")

'''
huawei

pre 0.5082217889716625
examined 
0.526246478680124
'''


