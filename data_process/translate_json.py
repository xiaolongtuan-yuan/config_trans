import os
import json
from tqdm import tqdm
from en_translator import translate_Zh2Eng

def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data

def translate_command_tree(config_json):
    for k, sub_dict in config_json.items():

        if not isinstance(sub_dict, dict):
            continue
        else:
            template_key = sub_dict.get("template")
            explanation_key = sub_dict.get("explanation")
            parameters_key = sub_dict.get("parameters")

            if explanation_key:
                translated_text = translate_Zh2Eng(sub_dict['explanation'])
                sub_dict['explanation'] = translated_text
            if parameters_key:
                for parameter in sub_dict['parameters']:
                    translated_text = translate_Zh2Eng(parameter['explanation'])
                    parameter['explanation'] = translated_text
        translate_command_tree(sub_dict)

    return config_json

if __name__ == '__main__':
    '''
    将原始json command json转换为command tree
    '''
    for vendor in ['HUAWEI']:
        source_dir = f'./experiment/train_dataset_rearrange/command_tree/{vendor}'
        save_dir = f'./experiment/train_dataset_rearrange/command_tree/{vendor}'

        for filename in tqdm(os.listdir(source_dir)):
            if filename.endswith('.json'):
                file_path = os.path.join(source_dir, filename)
                old_config = load_json_file(file_path)

                if not old_config:
                    continue
                new_config = translate_command_tree(old_config)

                save_path = os.path.join(save_dir, filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(new_config, f, ensure_ascii=False, indent=4)
