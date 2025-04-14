# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/12 16:04
@Auth ： xiaolongtuan
@File ：juniper_translate.py
"""
import pandas as pd

# 读取xlsx文件
df = pd.read_excel('JUNIPER_validation_set(no_answer)v2.xlsx')

# 遍历每一行数据
for index, row in df.iterrows():
    # 这里可以对每一行数据进行处理
    # 例如：打印每一行的数据
    origin_config = str(row['Origin'])
    df.at[index, 'translated'] = origin_config.upper()

df.to_excel('JUNIPER_validation_set_translated.xlsx', index=False)
