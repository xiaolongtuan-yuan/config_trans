#!/bin/bash
# 运行python脚本
conda activate trans
export PYTHONPATH=$(pwd)/..
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info