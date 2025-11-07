import json
from copy import deepcopy

def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def cross_validation(vendor1, vendor2, rule_libraries, module_matches, command_nodes):
    validated_rule_library = deepcopy(rule_libraries[f'{vendor2}_{vendor1}'])
    # 遍历所有的规则
    for rule, match in rule_libraries[f'{vendor1}_{vendor2}'].items():
        exist_mark = False
        for inversion_match in rule_libraries[f'{vendor2}_{vendor1}'].values():
            for inversion_rule in inversion_match:
                if rule in inversion_rule["trans_command"]:
                    exist_mark = True
                    break
        if not exist_mark and len(match) == 1:
            # 命令节点匹配非满射，则反转补充到rule_libraries[f'{vendor2}_{vendor1}']
            root = module_matches['{}_{}'.format(vendor2, vendor1)][match[0]['root']]
            # print(f"root: {root}")
            if rule not in command_nodes[vendor1][root].keys():
                continue
            parent_command = command_nodes[vendor1][root][rule]["structural_features"]["context_topology"]["parent_command"]
            # print(match[0]['para_map'])
            validated_rule = [{"para_map": match[0]['para_map'][::-1],    # 反转参数映射
                               "trans_command": rule,                      # 翻译命令
                               "parent_command": parent_command,                       # rule的父命令
                               "root": root}]
            # print('command:', match[0]["trans_command"], '/////mapping rule:', validated_rule)
            validated_rule_library[rule] = validated_rule
    return validated_rule_library


def load_module_match_libraries(vendor1, vendor2):
    """加载规则库"""
    rule_libraries = {}
    module_matches = {}
    command_nodes = {}
    rule_libraries[f'{vendor1}_{vendor2}'] = load_json_file(f'./dataset_multi_vendor_config/mapping_template_library/scale400/{vendor1}_{vendor2}.json')
    rule_libraries[f'{vendor2}_{vendor1}'] = load_json_file(f'./dataset_multi_vendor_config/mapping_template_library/scale400/{vendor2}_{vendor1}.json')
    module_matches[f'{vendor1}_{vendor2}'] = load_json_file(f'./dataset_multi_vendor_config/mapping_template_library/scale400/{vendor1}_{vendor2}_module_match.json')
    module_matches[f'{vendor2}_{vendor1}'] = load_json_file(f'./dataset_multi_vendor_config/mapping_template_library/scale400/{vendor2}_{vendor1}_module_match.json')
    command_nodes[vendor1] = load_json_file(f'./dataset_multi_vendor_config/config_command_node/scale400/{vendor1}.json')
    command_nodes[vendor2]= load_json_file(f'./dataset_multi_vendor_config/config_command_node/scale400/{vendor2}.json')
    return rule_libraries, module_matches, command_nodes

def main():
    vendor1 = 'Juniper'
    vendor2 =  'Cisco' # 'HUAWEI'
    rule_libraries, module_matches, command_nodes = load_module_match_libraries(vendor1, vendor2)
    validated_rule_library = cross_validation(vendor1, vendor2, rule_libraries, module_matches, command_nodes)
    with open(f'./dataset_multi_vendor_config/mapping_template_library/scale400/{vendor2}_{vendor1}.json', 'w', encoding='utf-8') as f:
        json.dump(validated_rule_library, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()