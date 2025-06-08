
# 查询missing template的原配置原件与目标配置文件以及template合集
import os
import ast
import json
import copy

def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def load_text_file(file_path):
    """加载文本文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def find_files(directory, extension):
    """查找指定目录下的所有文件"""
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(extension)]

def query_main(missing_temp, vendor1, vendor2):
    name = 'all_data_2000'
    num = 700
    scale = '680'
    folder_path = f'./exper_data/translated_config_with_{name}/{num}/{vendor1}/{vendor2}/'
    source_folder_path = f'./exper_data/translated_config_with_{name}/{num}//{vendor2}/{vendor1}/'
    result_extension = '_evaluate.json'
    label_extension = '_label_text.txt'
    # 获取所有匹配的文件
    result_files = find_files(folder_path.format(vendor1, vendor2), result_extension)
    find__flag = False
    for file_name in result_files:
        evaluate_data = load_json_file(file_name)
        if missing_temp in evaluate_data['missed_templates']:
           find__flag = True
           if file_name.startswith(folder_path) and file_name.endswith(result_extension):
            config_file = file_name[len(folder_path):-len(result_extension)] + label_extension
           break
    if find__flag:
        print(load_text_file(os.path.join(folder_path, config_file)))
        print('\n')
        print(load_text_file(os.path.join(source_folder_path, config_file)))
    else:
        print(f"未找到包含缺失模板 '{missing_temp}' 的配置文件。请检查输入的模板名称和路径。")
        return

def missing_template_peer_statistic_main():
    name = 'all_data_2000'
    num = 'valid_data_100_from_400&200'
    vendors = ['HUAWEI', 'Juniper', 'Cisco']
    for vendor1 in vendors:
        for vendor2 in vendors:
            if vendor1 == vendor2:
                continue
            folder_path = f'./exper_data/translated_config_with_{name}/{num}/{vendor1}/{vendor2}/'
            source_folder_path = f'./exper_data/translated_config_with_{name}/{num}//{vendor2}/{vendor1}/'
            # folder_path = f'./exper_data/translated_config_with_use_freq/400/{vendor1}/{vendor2}/'
            map_rule_extension = '_map_rules.json'
            label_template_extension = '_expected_temp.json'
            result_extension = '_evaluate.json'
            label_extension = '_label_text.txt'
            command_tree_extension = '_source_command_tree.json'
            # 获取所有匹配的文件
            result_files = find_files(folder_path.format(vendor1, vendor2), result_extension)

            for file_name in result_files:
                evaluate_data = load_json_file(file_name)
                if file_name.startswith(folder_path) and file_name.endswith(result_extension):
                    config_file = file_name[len(folder_path):-len(result_extension)] + label_extension
                    template_file = file_name[len(folder_path):-len(result_extension)] + label_template_extension
                    rule_mapping_file = file_name[:-len(result_extension)] + map_rule_extension
                    command_tree_file = file_name[:-len(result_extension)] + command_tree_extension

                # print(load_text_file(os.path.join(folder_path, config_file)))
                template_list = load_json_file(os.path.join(folder_path, template_file))
                # print('\n')
                # print(load_text_file(os.path.join(source_folder_path, config_file)))
                source_template_list = load_json_file(os.path.join(source_folder_path, template_file))

                # 读取匹配规则文件与命令树
                match_rule_data = load_json_file(rule_mapping_file)
                command_tree = load_json_file(command_tree_file)
                rest_template_list = copy.deepcopy(template_list)
                rest_source_template_list = copy.deepcopy(source_template_list)
                len_rest_list = len(rest_template_list)
                prefixs = list([command_tree[key]['template'] for key in command_tree.keys()])

                # print(f'prefixs: {prefixs}')
                map_rules = list([])
                # 将juniper配置模板补全
                if vendor1 == 'Juniper':
                    prefix = str('')
                    for map_rule_str, count in match_rule_data.items():
                        map_rule = ast.literal_eval(map_rule_str)
                        if map_rule[0] in prefixs:
                            prefix = map_rule[0]
                            # print(f'prefix: {prefix}')
                        else:
                            map_rule[0] = prefix + ' ' + map_rule[0]
                            # print(f'map_rule[0]: {map_rule[0]}')
                        map_rules.append(map_rule)
                        # print(f'map_rule: {map_rule}')
                else:
                    for map_rule_str, count in match_rule_data.items():
                        map_rule = ast.literal_eval(map_rule_str)
                        map_rules.append(map_rule)
                # 删除能够被映射到的目标模板，同时删除源模板
                LLM_trans_list = list([])
                for map_rule in map_rules:
                    for item in map_rule[1]:
                        if 'source' not in item.keys() and vendor2 != 'Juniper':
                            rest_template_list = [temp for temp in rest_template_list if temp != item['trans_command']]
                        elif 'source' not in item.keys():
                            trans_command = item['parent_command'][0] + ' ' + item['trans_command'] if item['parent_command'] else item['trans_command']
                            rest_template_list = [temp for temp in rest_template_list if temp != trans_command]
                    if 'source' not in item.keys() and len_rest_list > len(rest_template_list):
                        rest_source_template_list = [temp for temp in rest_source_template_list if temp != map_rule[0]]
                        len_rest_list = len(rest_template_list)
                    elif 'source' in item.keys():
                        LLM_trans_list.append(map_rule[0])
                unmatch_template = {'rule_source': rest_source_template_list, 'llm_source':LLM_trans_list ,'target': rest_template_list}
                # 保存数据
                save_path = rule_mapping_file = file_name[:-len(result_extension)] + '_unmatch_template.json'
                with open(save_path, mode='w', encoding='utf-8') as f:
                    json.dump(unmatch_template, f, ensure_ascii=False, indent=2)
                # return None


if __name__ == "__main__":
    # 示例调用
    '''missing_temp = 'tunnel-protocol [parameter1] [parameter2]'
    vendor1 = 'Juniper'
    vendor2 = 'HUAWEI'
    query_main(missing_temp, vendor1, vendor2)'''

    missing_template_peer_statistic_main()