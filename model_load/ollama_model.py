import requests
import json

def query_deepseek(prompt):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "deepseek-r1:7b",
        "prompt": prompt,
        "stream": False  # 流式传输设为True可实时接收输出
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()["response"]
    else:
        return f"Error: {response.text}"

# 调用示例
result = query_deepseek("用Python实现快速排序算法")
print(result)