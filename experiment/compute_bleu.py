# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:30
@Auth ： xiaolongtuan
@File ：compute_bleu.py
"""
import os

from langchain_community.embeddings import HuggingFaceEmbeddings
from nltk.translate.bleu_score import sentence_bleu
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def preprocess_text(text):
    # 去除注释（以#或!开头的行）
    lines = [line for line in text.splitlines() if not line.strip().startswith(('#', '!'))]
    # 去除中文词汇（保留ASCII字符）
    cleaned_text = ''.join(char for char in ' '.join(lines) if ord(char) < 128)
    return cleaned_text.split()

def clean_config_text(text):
    # 去除注释行（以#或!开头的行）和空行
    lines = [line for line in text.splitlines()
             if line.strip() and not line.strip().startswith(('#', '!', '*', '/*', '*/'))]
    return '\n'.join(lines)

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

def compute_embded_similarity(translated_dir, real_dir, config_files):
    local_EMmodel_path = '../EmbeddingModel/MiniLM-L6-v2'
    # embedding_model = SentenceTransformer(local_EMmodel_path)
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": "cuda:0"})
    total_similarity = 0.0
    count = 0
    for config_file in config_files:
        # 读取翻译后的配置文件
        with open(os.path.join(translated_dir, config_file), 'r') as f:
            translated_config = f.read()
        # 读取真实配置文件
        with open(os.path.join(real_dir, config_file), 'r') as f:
            real_config = f.read()
            real_words = clean_config_text(real_config)

        translated_embedding = embedding_model.embed_query(translated_config)
        real_embedding = embedding_model.embed_query(real_words)

        similarity = cosine_similarity(
            np.array(translated_embedding).reshape(1, -1),
            np.array(real_embedding).reshape(1, -1)
        )[0][0]

        total_similarity += similarity
        count += 1
    return total_similarity / count if count > 0 else 0.0


if __name__ == '__main__':
    scale = 2000
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    translated_config_base = './exper_data/cisco_translated_config_with_mapping_examined'

    for source_vendor in ['Cisco']:
        for target_vendor in vendors:
            if target_vendor == source_vendor:
                continue

            translated_config_dir = os.path.join(translated_config_base, str(scale), source_vendor, target_vendor)
            trannlated_config_files = [f for f in os.listdir(translated_config_dir) if f.endswith('.txt')]
            real_config_dir = f'./exper_data/lable/{target_vendor}'


            # 计算Cisco到Huawei的BLEU分数
            # score = compute_word_match_rate(translated_config_dir, real_config_dir, trannlated_config_files)
            score = compute_embded_similarity(translated_config_dir, real_config_dir, trannlated_config_files)
            print(f"scale {scale},{source_vendor} to {target_vendor} embded similarity: {score}")

'''
huawei

pre 0.5082217889716625
examined 
0.526246478680124

scale 2000,Cisco to HUAWEI embded similarity: 0.8599730785426216
scale 2000,Cisco to Juniper embded similarity: 0.5767573199858755
'''


