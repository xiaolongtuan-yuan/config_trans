from gradio_client import Client
import time

import httpx


def connect_test():
    url = "https://qwen-qwq-32b-preview.hf.space/"
    try:
        response = httpx.get(url)
        print(response.status_code)
        print(response.text)
    except httpx.ConnectError as e:
        print("连接失败:", e)


def huggingface_space(space_url):
    # 设置全局超时时间
    # httpx._config.DEFAULT_TIMEOUT_CONFIG = 60.0  # 60 秒超时
    # Hugging Face Space 的 URL
    # space_url = "https://qwen-qwq-32b-preview.hf.space/"
    # space_url = "https://huggingface.co/spaces/Nymbo/QwQ-32B-Preview-Serverless"

    # 初始化 Gradio 客户端
    client = Client(space_url)
    # print(client.view_api()) 查看接口

    # 用户输入
    user_input = "你好，请介绍一下你自己，并回答一加一等于几？"

    # 1. 调用 /add_text，将用户输入添加到聊天历史中
    try:
        print("正在添加用户输入...")
        _, updated_chatbot = client.predict(
            _input={"files": [], "text": user_input},  # 用户输入
            _chatbot=[],  # 初始聊天历史为空
            api_name="/add_text"
        )
        print("更新后的聊天历史：", updated_chatbot)
    except Exception as e:
        print("调用 /add_text 失败：", str(e))
        exit()

    # 2. 调用 /agent_run，触发模型生成回答
    try:
        print("正在触发模型生成回答...")
        result = client.predict(
            _chatbot=updated_chatbot,  # 传入更新后的聊天历史
            api_name="/agent_run"
        )
        print("模型回答：", result)
    except Exception as e:
        print("调用 /agent_run 失败：", str(e))
    '''try:
        print("正在调用模型...")
        result = client.predict(
            _input={"files":[],"text":input_text},
		    _chatbot=[], 
            api_name="/add_text")
        print("模型输出：", result)

        # 保存输出到文件
        output_file = "model_output.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"模型输出已保存到 {output_file}")

    except Exception as e:
        print("调用模型时出错：", str(e))'''


if __name__ == "__main__":
    space_url = "https://qwen-qwq-32b-preview.hf.space/"
    huggingface_space(space_url)