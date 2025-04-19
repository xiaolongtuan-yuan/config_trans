import re
import json

def split_parameters(text):
    pattern = re.compile(r'(\[parameter\d+\])|([^[\]]+)')
    segments = []
    current_text = ''
    current_params = []

    for match in pattern.finditer(text):
        if match.group(1):
            # 处理参数部分
            param = match.group(1)
            param_num = int(re.search(r'parameter(\d+)', param).group(1))
            current_params.append(param_num)
            current_text += param
        else:
            # 处理非参数部分
            non_param = match.group(2)
            if re.search(r'[^\s/]', non_param):
                if current_text or current_params:
                    segments.append({'text': current_text.strip(), 'params': current_params.copy()})
                    current_text = non_param
                    current_params = []
                else:
                    current_text += non_param
            else:
                current_text += non_param

    if current_text or current_params:
        segments.append({'text': current_text.strip(), 'params': current_params.copy()})
    
    # 提取结果和参数集合
    result_segments = [seg['text'] for seg in segments]
    param_sets = [seg['params'] for seg in segments]
    # print(param_sets)
    
    # 格式化参数输出
    '''formatted_params = []
    for s in param_sets:
        sorted_params = sorted(s)
        if len(sorted_params) == 1:
            formatted_params.append('{' + str(sorted_params[0]) + '}')
        else:
            formatted_params.append('{' + ', '.join(map(str, sorted_params)) + '}')'''
    
    return result_segments, param_sets

def load_txt(txt_file_path):
    txt_data = []
    with open(txt_file_path, 'r') as file:
        # 读取文件的所有行
        lines = file.readlines()
    # 打印每一行
    for line in lines:
        # print(line.strip())  # 使用strip去除每行末尾的换行符
        txt_data.append(line.strip())
    return txt_data

# save JSON fie
def save_json_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as json_file:
        # json.dump(data, json_file, indent=4)
        json.dump(data, json_file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    txt_file_path = 'commands/Juniper_commands.txt'
    save_file_path = 'commands/decompose_Juniper_commands.json'
    command_data = load_txt(txt_file_path)
    # 示例输入
    # text = "set interfaces [parameter1] unit [parameter2] [parameter3] family inet address [parameter4]/[parameter5]"
    decompose_commands = {}
    for command in command_data:
        segments, params = split_parameters(command)
        print("划分后的段：")
        print(segments)
        print("每个段的参数集合：")
        print(params)
        decompose_commands[command] = [segments, params]
    save_json_file(decompose_commands, save_file_path)
    
