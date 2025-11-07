import json

# load JSON fie and load data
def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data

# save JSON fie
def save_json_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as json_file:
        # json.dump(data, json_file, indent=4)
        json.dump(data, json_file, ensure_ascii=False, indent=4)

def subdivision_config_model(decompose_commands:dict, old_config_model:dict):
    subdivision_model = {}
    for command, seg in decompose_commands.items():
        command_node = old_config_model[command]
        # print(command_node['parameters'])
        segments = seg[0]
        paras = seg[1]
        sub_model = subdivision_model
        # print(segments, paras)
        for k_part in range(len(segments)):
            segment = segments[k_part]
            if not sub_model.get(segment):
                if len(segments) == 1:
                    sub_model[segment] = { "template": segment,
                                            "command": "",
                                            "explanation": command_node['explanation'],
                                            "parameters": [command_node['parameters'][i-1] for i in paras[k_part]]}
                else:
                    sub_model[segment] = { "template": segment,
                                            "command": "",
                                            "explanation": "",
                                            "parameters": [command_node['parameters'][i-1] for i in paras[k_part]]}
            sub_model = sub_model[segment]
    return subdivision_model

if __name__ == "__main__":
    decompose_command_path = "dataset_multi_vendor_config/config_command_node/commands/decompose_Juniper_commands.json"
    old_model_path = 'dataset_multi_vendor_config/config_model/scale388en/Juniper_en.json'
    decompose_commands = load_json_file(decompose_command_path)
    old_config_model = load_json_file(old_model_path)

    subdivision_model = subdivision_config_model(decompose_commands, old_config_model)

    save_path = 'dataset_multi_vendor_config/config_model/scale388en/subdivision_Juniper_en.json'
    save_json_file(subdivision_model, save_path)

