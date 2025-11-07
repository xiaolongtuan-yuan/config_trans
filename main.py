# -*- coding: utf-8 -*-
"""
@Time ： 2025/5/7 15:21
@Auth ： xiaolongtuan
@File ：main.py
"""
import time
import torch

def occupy_1GB_gpu():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    num_floats = 1_073_741_824 // 4
    dummy_tensor = torch.empty(int(num_floats), dtype=torch.float32, device=device)
    return dummy_tensor

if __name__ == "__main__":
    dummy = occupy_1GB_gpu()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Process terminated manually.")