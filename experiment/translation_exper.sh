#!/bin/bash

# 删除上次运行结果
rm -rf ./exper_data/cisco_translated_config
# 运行python脚本
export PYTHONPATH=$(pwd)/..
python -u exper_data_translated.py