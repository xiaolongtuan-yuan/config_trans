import os
import torch
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ["CUDA_VISIBLE_DEVICES"] = "1" 
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

model_name = "Qwen/QwQ-32B-Preview"
# model_name = "Qwen/Qwen2.5-14B-Instruct"
# model_name = "Qwen/Qwen2.5-7B-Instruct"
# 配置 4-bit 量化

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,  # 启用 4-bit 量化
    bnb_4bit_compute_dtype=torch.float16,  # 指定计算时的精度
    bnb_4bit_use_double_quant=True,  # 启用双量化以节省显存
    bnb_4bit_quant_type="nf4"  # 使用 NF4 量化类型（更精确的 4-bit 表示）
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto",
    quantization_config=quantization_config  # 使用 BitsAndBytesConfig
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

prompt = """
请按照以下格式将思科配置解析成 JSON 格式。每条配置命令作为一个节点，配置命令作为节点键值，配置命令需要解析出模板 "template"、命令示例 "command" 以及命令解释 "explanation"。每个配置中的参数被逐个解析出作为节点中的列表 "parameters"，每个参数需要解析出参数名 "name"、参数类型 "type" 与参数解释 "explanation"。如果配置命令有次级配置命令，直接作为其子节点，节点内容分析按照前面所述。

### 示例：
配置命令：
hostname DeviceA

interface GigabitEthernet1/0/0
 no shutdown
 ip address 1.1.1.1 255.0.0.0

对应 JSON 格式：
{
  "hostname DeviceA": {
    "template": "hostname [parameter1]",
    "command": "hostname DeviceA",
    "explanation": "设置设备的主机名为 'DeviceA'",
    "parameters": [
       {
        "name":"host name",
        "type": "string",
        "explanation":"主机名"
       } 
    ]
  },
  "interface GigabitEthernet1/0/0": {
      "template": "interface [parameter1]",
      "command": "interface GigabitEthernet1/0/0",
      "explanation": "配置接口 'GigabitEthernet1/0/0'",
      "parameters": [
        {
          "name":"interface name",
          "type": "string",
          "explanation":"接口名"
        }
      ],
      "no shutdown": {
          "template": "no shutdown",
          "command": "no shutdown",
          "explanation": "启用接口（默认情况下接口是关闭的）",
          "parameters": []
      },
      "ip address 1.1.1.1 255.0.0.0": {
          "template": "ip address [parameter1] [parameter2]",
          "command": "ip address 1.1.1.1 255.0.0.0",
          "explanation": "配置接口的 IPv4 地址为 1.1.1.1，子网掩码为 255.0.0.0",
          "parameters": [
            {
              "name":"ip address",
              "type": "IPv4",
              "explanation":"IPv4 地址"
            },
            {
              "name":"subnet mask",
              "type": "IPv4",
              "explanation":"子网掩码"
            }
          ]
      }
  }
}

### 任务：
请将以下配置转换为 JSON 格式(注意，直接输出以下配置对应的JSON格式即可，其他内容无需输出)：
{配置命令}
"""

messages = [
    {"role": "system", "content": "You are a helpful assistant specialized in network configuration analysis and transformation. Think step-by-step and provide detailed explanations."}, 
    {"role": "user", "content": prompt}
]

# test 
cisco_config = """
hostname Spoke1

interface GigabitEthernet1/0/0
 ip address 10.1.2.10 255.255.255.0
 tunnel source Loopback0
 tunnel mode gre multipoint
 tunnel protection ipsec profile <IPSEC_PROFILE_NAME>

interface Loopback0
 ip address 192.168.1.1 255.255.255.255

interface Tunnel0
 ip address 172.16.1.2 255.255.255.0
 tunnel source GigabitEthernet1/0/0
 tunnel mode gre multipoint
 tunnel protection ipsec profile <IPSEC_PROFILE_NAME>

router ospf 1
 router-id 172.16.1.2
 network 172.16.1.0 0.0.0.255 area 0
 network 192.168.1.0 0.0.0.255 area 0

router ospf 2
 router-id 10.1.2.10
 network 10.1.2.0 0.0.0.255 area 1
"""
formatted_prompt = prompt.replace("{配置命令}", cisco_config)
messages[1]["content"] = formatted_prompt

text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

'''generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=512  # 可提高生成的最大新 tokens 数，1024/2048
)
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]

response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
print(response)'''

total_response = ""
max_new_tokens_per_round = 2048
response_round = 0
while True:
    print('response_round=', response_round)
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=max_new_tokens_per_round
    )
    new_response = tokenizer.batch_decode(generated_ids[:, model_inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
    print(new_response)
    total_response += new_response
    
    if len(new_response) < max_new_tokens_per_round or response_round > 4:
        break
    
    # 将当前的输出作为新的输入
    new_text = tokenizer.apply_chat_template(
        messages + [{"role": "assistant", "content": total_response}],
        tokenize=False,
        add_generation_prompt=True
    )
    model_inputs = tokenizer([new_text], return_tensors="pt").to(model.device)
    response_round += 1

print(total_response)

