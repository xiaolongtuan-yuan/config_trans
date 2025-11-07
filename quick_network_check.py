#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速网络检查脚本
专门用于检查 DeepSeek API 连接
"""

import os
import time
import requests
from openai import OpenAI, APITimeoutError, APIConnectionError

def quick_deepseek_check():
    """快速检查DeepSeek API连接"""
    print("=" * 50)
    print("DeepSeek API 快速连接检查")
    print("=" * 50)
    
    # 1. 检查API Key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("✗ 错误: DEEPSEEK_API_KEY 环境变量未设置")
        print("请设置: export DEEPSEEK_API_KEY='your_api_key'")
        return False
    
    print(f"✓ API Key 存在 (长度: {len(api_key)})")
    
    # 2. 检查基本网络
    print("检查基本网络连接...")
    
    # 尝试多个测试端点
    test_urls = [
        "https://www.baidu.com",
        "https://httpbin.org/get", 
        "http://httpbin.org/get",  # HTTP版本作为备选
        "https://api.github.com"
    ]
    
    network_ok = False
    for url in test_urls:
        try:
            print(f"  测试 {url}...")
            response = requests.get(url, timeout=10, verify=False)  # 跳过SSL验证
            if response.status_code == 200:
                print(f"✓ 基本网络连接正常 ({url})")
                network_ok = True
                break
        except Exception as e:
            print(f"  {url} 失败: {str(e)[:50]}...")
            continue
    
    if not network_ok:
        print("✗ 所有网络测试都失败，可能是VPN或防火墙问题")
        print("建议: 检查VPN设置或尝试禁用VPN")
        return False
    
    # 3. 测试DeepSeek API
    print("测试DeepSeek API连接...")
    try:
        client = OpenAI(
            api_key=api_key,
            base_url='https://api.deepseek.com/v1',
            timeout=30.0
        )
        
        start_time = time.time()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            timeout=30
        )
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        result = response.choices[0].message.content
        
        print(f"✓ DeepSeek API 连接成功")
        print(f"✓ 响应时间: {response_time:.2f}ms")
        print(f"✓ 模型响应: {result}")
        
        if response_time > 10000:
            print("⚠ 警告: 响应时间较长，可能导致超时")
        
        return True
        
    except APITimeoutError as e:
        print(f"✗ DeepSeek API 连接超时: {str(e)}")
        print("建议: 检查网络延迟或增加超时时间")
        return False
    except APIConnectionError as e:
        print(f"✗ DeepSeek API 连接错误: {str(e)}")
        print("建议: 检查网络连接和防火墙设置")
        return False
    except Exception as e:
        print(f"✗ DeepSeek API 连接失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = quick_deepseek_check()
    print("\n" + "=" * 50)
    if success:
        print("✓ 网络连接检查通过，可以正常使用DeepSeek API")
    else:
        print("✗ 网络连接检查失败，请检查上述错误信息")
    print("=" * 50)
