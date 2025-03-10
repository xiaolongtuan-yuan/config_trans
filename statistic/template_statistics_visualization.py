# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/10 00:53
@Auth ： xiaolongtuan
@File ：template_statistics_visualization.py
"""
import json

import matplotlib.pyplot as plt
from wordcloud import WordCloud
import numpy as np

# Load data from JSON file
vendors = ["Cisco", "Juniper", "Huawei"]
for vendor in vendors:
    with open(f"./statistic_res/{vendor}_template_used_statistic.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    '''
    data = {
        "sysname [parameter1]": 131,
        "multicast routing-enable": 175,
        "interface [parameter1]": 546,
        "ospf [parameter1]": 793
    }
    '''

    # Generate word frequency data
    word_freq = data

    if vendor == "Juniper":
        top_n = 200
        top_word_freq = dict(sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:top_n])
        wordcloud = WordCloud(width=1000, height=500, background_color='white',prefer_horizontal=1.0).generate_from_frequencies(top_word_freq)
    elif vendor == "Huawei":
        top_n = 500
        top_word_freq = dict(sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:top_n])
        wordcloud = WordCloud(width=1000, height=500, background_color='white').generate_from_frequencies(top_word_freq)

    else:
        top_n = 300
        top_word_freq = dict(sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:top_n])
        wordcloud = WordCloud(width=1000, height=500, background_color='white').generate_from_frequencies(top_word_freq)

    # Plot word cloud
    plt.figure(figsize=(10, 6))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(f'{vendor} Template Usage Frequency Word Cloud')
    plt.savefig(f"./statistic_res/{vendor}_template_usage_frequency_word_cloud.png")


    # Generate Cumulative Distribution Function (CDF) plot
    total_count = sum(data.values())  # 计算总次数
    probabilities = [count / total_count for count in data.values()]

    sorted_probabilities = np.sort(probabilities)
    cumulative_probs = np.cumsum(sorted_probabilities)

    # Plot CDF
    plt.figure(figsize=(10, 6))
    plt.plot(sorted_probabilities, cumulative_probs, marker='o', linestyle='-')
    plt.xlabel('Probability')
    plt.ylabel('Cumulative Probability')
    plt.title(f'{vendor} Template Usage Probability Cumulative Distribution Function (CDF)')
    plt.grid(True)
    plt.savefig(f"./statistic_res/{vendor}_template_usage_probability_CDF.png")