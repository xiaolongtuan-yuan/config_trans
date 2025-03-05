from pathlib import Path
import os
import torch
from tqdm import tqdm
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ["CUDA_VISIBLE_DEVICES"] = "0" 
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

def get_txt_filenames(folder_path):
    folder = Path(folder_path)
    txt_filenames = [str(file.name) for file in folder.rglob('*.txt')]
    return txt_filenames

def load_config(file_name, file_path):
    with open(file_path + '/' + file_name, 'r', encoding='utf-8') as file:
        config = file.read()
    return config

def save_parsed_config(parsed_file_path, file_mane, parsed_config):
    with open(parsed_file_path + '/' + file_mane, 'w', encoding='utf-8') as file:
        file.write(parsed_config)

model_name = "Qwen/QwQ-32B-Preview"
# model_name = "Qwen/Qwen2.5-14B-Instruct"

def model_load(model_name):
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
        quantization_config=quantization_config,  # 使用 BitsAndBytesConfig
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    return model, tokenizer

def prompt_massage_for_vendors(vendor):
    if vendor == 'Cisco':
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
        massages = [
            {"role": "system", "content": "You are a helpful assistant specialized in network configuration analysis and transformation. Think step-by-step and provide detailed explanations."},
            {"role": "user", "content": prompt}
        ]
    elif vendor == 'HUAWEI':
        prompt = """
            请按照以下格式将华为配置解析成 JSON 格式。每条配置命令作为一个节点，配置命令作为节点键值，配置命令需要解析出模板 "template"、命令示例 "command" 以及命令解释 "explanation"。每个配置中的参数被逐个解析出作为节点中的列表 "parameters"，每个参数需要解析出参数名 "name"、参数类型 "type" 与参数解释 "explanation"。如果配置命令有次级配置命令，直接作为其子节点，节点内容分析按照前面所述。

            ### 示例：
            配置命令：
            sysname PE2

            interface GigabitEthernet1/0/0
                undo shutdown
                ip address 192.168.0.1 255.255.255.0

            对应 JSON 格式：
            {
            "sysname PE2": {
                "template": "sysname [parameter1]",
                "command": "sysname PE2",
                "explanation": "设置设备的主机名为 'PE2'",
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
                "explanation": "...'",
                "parameters": 
                [
                    {
                    "name":"interface name",
                    "type": "string",
                    "explanation":"接口名"
                    }
                ],
                "undo shutdown": {
                    "template": "undo shutdown",
                    "command": "undo shutdown",
                    "explanation": "启用接口 (默认情况下接口是关闭的)",
                    "parameters": []
                    },
                "ip address 192.168.0.1 255.255.255.0":{
                    "template": "ip address [parameter1] [parameter2]",
                    "command": "ip address 192.168.0.1 255.255.255.0",
                    "explanation": "配置接口的IPv4地址为 192.168.0.1，子网掩码为 255.255.255.0",
                    "parameters": [
                    {
                        "name":"ip address",
                        "type": "IPv4",
                        "explanation":"IPv4地址"
                        } ,
                        {
                        "name":"sub musk",
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
        massages = [
            {"role": "system", "content": "You are a helpful assistant specialized in network configuration analysis and transformation. Think step-by-step and provide detailed explanations."},
            {"role": "user", "content": prompt}
        ]
    elif vendor == 'Juniper':
        prompt = """
            请上述形式将下列Juniper配置解析成json格式。每一条配置命令作为一个节点，配置命令作为节点键值，配置命令需要解析出模板"template"、命令示例"command"以及命令解释"explanation"，每个配置中的参数被逐个解析出作为节点中的list"parameters"，每个参数需要解析出参数名"name"、参数类型"type"与参数解释"explanation"。如果多条配置命令有相同的命令前缀（前两个或前三个单词），将命令前缀提炼为父节点，这多条配置命令做为其子节点，子节点节点内容分析按照前面所述。

            ### 示例：
            配置命令：
            set system host-name Hub

            set interfaces ge-1/0/0 unit 0 family inet address 10.1.1.10/24
            set interfaces lo0 unit 0 family inet address 192.168.0.1/32

            对应 JSON 格式：
            {
            "set system": {
                "set system host-name Hub": {
                "template": "set system host-name [parameter1]",
                "command": "set system host-name Hub",
                "explanation": "配置设备的主机名。",
                "parameters": [
                    {
                    "name": "hostname",
                    "type": "string",
                    "explanation": "设备的主机名，用于标识网络中的设备。"
                    }
                ]
                }
            },
            "set interfaces": {
                    "set interfaces ge-1/0/0 unit 0 family inet address 10.1.1.10/24": {
                        "template": "set interfaces [parameter1] unit [parameter2] family inet address [parameter3]/[parameter4]",
                        "command": "set interfaces ge-1/0/0 unit 0 family inet address 10.1.1.10/24",
                        "explanation": "配置接口的IPv4地址及子网掩码。",
                        "parameters": [
                        {
                            "name": "interface",
                            "type": "string",
                            "explanation": "接口名称，例如ge-1/0/0。"
                        },
                        {
                            "name": "unit",
                            "type": "integer",
                            "explanation": "接口单元号，用于区分同一接口下的多个逻辑配置。"
                        },
                        {
                            "name": "ip-address",
                            "type": "string",
                            "explanation": "分配给接口的IPv4地址。"
                        },
                        {
                            "name": "subnet-mask",
                            "type": "integer",
                            "explanation": "IPv4子网掩码的位数。"
                        }
                        ]
                    }
                    },
                    "set interfaces lo0 unit 0 family inet address 192.168.0.1/32": {
                        "template": "set interfaces [parameter1] unit [parameter2] family inet address [parameter3]/[parameter4]",
                        "command": "set interfaces lo0 unit 0 family inet address 192.168.0.1/32",
                        "explanation": "配置环回接口的IPv4地址及子网掩码。",
                        "parameters": [
                        {
                            "name": "interface",
                            "type": "string",
                            "explanation": "接口名称，例如lo0。"
                        },
                        {
                            "name": "unit",
                            "type": "integer",
                            "explanation": "接口单元号，用于区分同一接口下的多个逻辑配置。"
                        },
                        {
                            "name": "ip-address",
                            "type": "string",
                            "explanation": "分配给接口的IPv4地址。"
                        },
                        {
                            "name": "subnet-mask",
                            "type": "integer",
                            "explanation": "IPv4子网掩码的位数。"
                        }
                        ]
                    }
                    }

            ### 任务：
            请将以下配置转换为 JSON 格式(注意，直接输出以下配置对应的JSON格式即可，其他内容无需输出)：
            {配置命令}
            """
        massages = [
            {"role": "system", "content": "You are a helpful assistant specialized in network configuration analysis and transformation. Think step-by-step and provide detailed explanations."},
            {"role": "user", "content": prompt}
        ]
    
    return prompt, massages


def parse_config(model, tokenizer, prompt, messages, config):
    formatted_prompt = prompt.replace("{配置命令}", config)
    messages[1]["content"] = formatted_prompt

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    '''generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=1024  # 可提高生成的最大新 tokens 数，1024/2048
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]'''
    total_response = ""
    max_new_tokens_per_round = 4096
    response_round = 0
    while True:
        # print('response_round=', response_round)
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens_per_round
        )
        new_response = tokenizer.batch_decode(generated_ids[:, model_inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
        print(new_response)
        total_response += new_response
        
        if len(new_response) < max_new_tokens_per_round or response_round > 5:
            break
        
        # 将当前的输出作为新的输入
        new_text = tokenizer.apply_chat_template(
            messages + [{"role": "assistant", "content": total_response}],
            tokenize=False,
            add_generation_prompt=True
        )
        model_inputs = tokenizer([new_text], return_tensors="pt").to(model.device)
        response_round += 1

    return total_response


if __name__ == "__main__":
    ## 获取文件名
    folder_path = 'config_trans/dataset_multi_vendor_config/config_data_1-400/Juniper'  # 请将此处替换为你实际的文件夹路径
    txt_files = get_txt_filenames(folder_path)
    # print(txt_files)
    ## 加载模型
    model_name = "Qwen/QwQ-32B-Preview"
    model, tokenizer = model_load(model_name)
    ## 配置加载
    vendor = "HUAWEI"                 # 'Juniper'
    config_path =  'config_trans/dataset_multi_vendor_config/config_data_1-400/{}'.format(vendor) # 解析加载思科的配置
    save_path = 'config_trans/dataset_multi_vendor_config/parsed_config/{}'.format(vendor)
    ## 逐一解析配置
    for i in tqdm(range(len(txt_files))):
        config_file = txt_files[i]
        # 加载prompt, messages
        prompt, messages = prompt_massage_for_vendors(vendor)
        config = load_config(config_path, config_file)
        print(config)
        response = parse_config(model, tokenizer, prompt, messages, config)
        print(response)
        save_parsed_config(save_path, config_file, response)

