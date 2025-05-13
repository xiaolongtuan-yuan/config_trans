# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:28
@Auth ： xiaolongtuan
@File ：tree_match.py
"""
import ast
import os
import json
import re
from collections import defaultdict, Counter

from sqlalchemy.sql.coercions import expect

from experiment.syntax_correctness import find_template, load_config_model


def parse_config_file(file_path, config_model):
    """解析配置文件为模板序列"""
    templates = []
    extra_commands = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 去除前后空格和缩进
            command = line.strip()
            if command.startswith(('#', '!', '*', '/*', '*/')): # 注释行
                continue
            if command:
                template = find_template(command, config_model)
                if template:
                    templates.append(template.lower())
                else:
                    extra_commands.append(command.lower())
    return templates, extra_commands


def parse_config_file_intact(file_path):
    """解析配置文件为命令列表"""
    commands = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 去除前后空格和缩进
            command = line.strip()
            if command.startswith(('#', '!', '*', '/*', '*/')): # 注释行
                continue
            if command:
                commands.append(command.lower())
    # commands = set(commands)
    return commands

def parse_config_file_content_intact(file_content):
    """解析配置文件为命令列表"""
    commands = []
    for line in file_content.split('\n'):
        # 去除前后空格和缩进
        command = line.strip()
        if command.startswith(('#', '!', '*', '/*', '*/')):  # 注释行
            continue
        if command:
            commands.append(command.lower())
    return commands


def calculate_match_ratio(result_templates, expected_templates, result_extra_commands, expected_extra_commands):
    """计算翻译的模板序列的匹配度"""
    match_count = 0
    error_templates = []
    for expected_template in expected_templates:
        if expected_template in result_templates:
            match_count += 1
        else:
            error_templates.append(expected_template)

    for expected_extra_command in expected_extra_commands:
        if expected_extra_command in result_extra_commands:
            match_count += 1
            # expected_extra_commands.remove(result_extra_command)
        else:
            error_templates.append(expected_extra_command)

    return match_count, (len(expected_templates) + len(expected_extra_commands)), error_templates

def para_extract(src_cmd: str, src_template: str) -> str:
    # print(src_cmd, src_template)
    # 将源模板转换为正则表达式
    # 例如 "hostname [parameter1]" -> r"hostname (\S+)"
    if bool(re.search(r"\[[^\]]+\]", src_template)):
        src_regex = re.sub(r"\[[^\]]+\]", r"(\\S+)", src_template)
    else:
        src_regex = re.escape(src_template)
    # 匹配源命令并提取参数
    try:
        match = re.match(src_regex, src_cmd)
    except re.error:
        return []
    if not match:
        # raise ValueError(f"源命令 '{src_cmd}' 不匹配模板 '{src_template}'")
        return []
    # 提取参数
    parameters = match.groups()
    return parameters

def get_template_info(template, config_model):
    """递归查找命令对应的模板"""
    for k, details in config_model.items():
        if k == 'template':
            if details == template:
                return config_model
        # 递归查找子命令
        if isinstance(details, dict) and 'template' in details:
            sub_template = get_template_info(template, details)
            if sub_template:
                return sub_template
    return None

def llm_command_accuracy_cal(expect_templates:[], trans_commands:[], expected_commands:[], config_model:{}):
    # 计算参数准确率
    trans_params = []
    expected_params = []
    command_match_score = 0

    template_match_score = 0
    denominator = len(trans_commands)

    expected_template_counter = Counter(expect_templates)
    for template in expected_template_counter.keys():
        res_param_strs = []
        label_param_strs = []

        template_info = get_template_info(template, config_model)
        # 如果是与名字相关的参数，我们不计入准确率
        ignore_param_index = []
        for index, parameter in enumerate(template_info.get('parameters', [])):
            if 'name' in parameter['explanation'].lower():
                ignore_param_index.append(index)

        template_re = re.sub(r"\[[^\]]+\]", r'(\\S+)', template)
        commands_to_remove = []
        is_match = False
        for command in trans_commands:
            # 判断命令是否匹配模板
            if re.match(template_re, command):
                is_match = True
                # 提取参数
                res_parameters = list(para_extract(command, template))
                res_parameters = [parameter for index, parameter in enumerate(res_parameters) if index not in ignore_param_index]

                trans_params.extend(res_parameters) # 总参数
                res_param_strs.append(str(res_parameters)) # 被参数代替了的命令

                commands_to_remove.append(command)
        for command in commands_to_remove:
            trans_commands.remove(command)
        if is_match:
            template_match_score += expected_template_counter[template]

        commands_to_remove = []
        for command in expected_commands:
            if re.match(template_re, command):
                lebel_parameters = list(para_extract(command, template))
                lebel_parameters = [parameter for index, parameter in enumerate(lebel_parameters) if index not in ignore_param_index]

                expected_params.extend(lebel_parameters)
                label_param_strs.append(str(lebel_parameters))
                commands_to_remove.append(command)
        for command in commands_to_remove:
            expected_commands.remove(command)

        for label_param_str in label_param_strs:
            if label_param_str in res_param_strs:
                command_match_score += 1
                res_param_strs.remove(label_param_str)

    for label_command in expected_commands:
        if label_command in trans_commands:
            command_match_score += 1

    param_match_score = [param for param in expected_params if param in trans_params]
    param_match_ratio = len(param_match_score) / len(expected_params) if len(expected_params) > 0 else 0
    command_match_ratio = command_match_score / denominator if denominator > 0 else 0
    template_match_ratio = template_match_score / len(expect_templates) if len(expect_templates) > 0 else 0


    return command_match_ratio, param_match_ratio, template_match_ratio

class command_data:
    def __init__(self,id, command, source):
        self.id = id
        self.command = command
        self.source = source
    def set_simplify_command(self, simplified_command):
        # 去除掉命名参数后的命令
        self.simplified_command = simplified_command
        return

def trans_command_preprocess(trans_commands:[], llm_trans_commands:[]):
    id = 0
    trans_command_datas = []
    for command in [data for data in trans_commands if data not in llm_trans_commands]:
        trans_command_datas.append(command_data(id, command, 'rule'))
        id += 1
    for command in llm_trans_commands:
        trans_command_datas.append(command_data(id, command, 'llm'))
        id += 1
    return trans_command_datas

def command_template_process(expect_templates:[], trans_commands:[], llm_trans_commands:[], expected_commands:[], config_model:{}):
    trans_command_datas = trans_command_preprocess(trans_commands, llm_trans_commands)

    trans_params = []
    expected_params = []
    command_match_score = 0
    llm_command_match_score = 0
    template_match_score = 0
    denominator = len(expected_commands)

    expected_template_counter = Counter(expect_templates)
    used_simplifoed_data_id = []
    for template in expected_template_counter.keys():
        res_simplifoed_data = []
        label_param_strs = []
        template_info = get_template_info(template, config_model)
        ignore_param_index = [] # 如果是与名字相关的参数，我们不计入准确率
        for index, parameter in enumerate(template_info.get('parameters', [])):
            if 'name' in parameter['explanation'].lower():
                ignore_param_index.append(index)

        template_re = re.sub(r"\[[^\]]+\]", r'(\\S+)', template)
        commands_to_remove = []
        is_match = False
        for command_data in [data for data in trans_command_datas if data.id not in commands_to_remove]:
            # 判断命令是否匹配模板
            if re.match(template_re, command_data.command):
                is_match = True
                # 提取参数
                res_parameters = list(para_extract(command_data.command, template))
                res_parameters = [parameter for index, parameter in enumerate(res_parameters) if index not in ignore_param_index]

                trans_params.extend(res_parameters) # 总参数
                command_data.set_simplify_command(str(res_parameters))
                res_simplifoed_data.append(command_data) # 被参数代替了的命令

                commands_to_remove.append(command_data.id)
        # for command in commands_to_remove:
        #     trans_commands.remove(command)

        if is_match:
            template_match_score += expected_template_counter[template]

        commands_to_remove = []
        for command in expected_commands:
            if re.match(template_re, command):
                lebel_parameters = list(para_extract(command, template))
                lebel_parameters = [parameter for index, parameter in enumerate(lebel_parameters) if index not in ignore_param_index]

                expected_params.extend(lebel_parameters)
                label_param_strs.append(str(lebel_parameters))
                commands_to_remove.append(command)
        for command in commands_to_remove:
            expected_commands.remove(command)

        for label_param_str in label_param_strs:
            for res_simplifoed_data_item in [data for data in res_simplifoed_data if data.id not in used_simplifoed_data_id]:
                if label_param_str == res_simplifoed_data_item.simplified_command:
                    command_match_score += 1
                    if res_simplifoed_data_item.source == 'llm':
                        llm_command_match_score += 1
                    used_simplifoed_data_id.append(res_simplifoed_data_item.id)
                    break

    for label_command in expected_commands:
        for res_simplifoed_data_item in [data for data in trans_command_datas if data.id not in used_simplifoed_data_id]:
            if label_command == res_simplifoed_data_item.command:
                command_match_score += 1
                if res_simplifoed_data_item.source == 'llm':
                    llm_command_match_score += 1
                break

    param_match_score = [param for param in expected_params if param in trans_params]
    param_match_ratio = len(param_match_score) / len(expected_params) if len(expected_params) > 0 else 0
    command_match_ratio = command_match_score / denominator if denominator > 0 else 0
    template_match_ratio = template_match_score / len(expect_templates) if len(expect_templates) > 0 else 0
    llm_command_match_ratio = llm_command_match_score / denominator if denominator > 0 else 0
    rule_command_match_ratio = (command_match_score - llm_command_match_score) / denominator if denominator > 0 else 0


    return {
        'command_match_ratio': command_match_ratio,
        'param_match_ratio': param_match_ratio,
        'template_match_ratio': template_match_ratio,
        'llm_command_match_ratio': llm_command_match_ratio,
        'rule_command_match_ratio': rule_command_match_ratio
    }

def cul_command_and_param_accuracy(translated_dir, real_dir, config_files):
    total_command_match_ratio = []
    total_param_match_ratio = []
    total_template_match_ratio = []
    total_llm_command_match_ratio = []
    total_rule_command_match_ratio = []
    for file_name in config_files:
        file_result = os.path.join(translated_dir, file_name)
        command_tree_path = file_result.replace('.txt', '_label_command_tree.json')
        evaluate_json_path = file_result.replace('.txt', '_evaluate.json')
        if not os.path.exists(command_tree_path):
            command_tree_dir = real_dir.replace('text_config', 'command_tree')
            command_tree_path = os.path.join(command_tree_dir, file_name.replace('.txt', '.json'))

        real_command_tree = load_config_model(command_tree_path)
        expect_temp = get_all_templates(real_command_tree)
        file_expected = os.path.join(real_dir, file_name)
        evaluate_json = load_config_model(evaluate_json_path)

        result_commands = parse_config_file_intact(file_result)
        llm_trans_commands = evaluate_json['llm_trans_commands']
        expected_commands = parse_config_file_intact(file_expected)
        accuracy_dict = command_template_process(expect_temp, result_commands, llm_trans_commands, expected_commands, real_command_tree)



        total_command_match_ratio.append(accuracy_dict['command_match_ratio'])
        total_param_match_ratio.append(accuracy_dict['param_match_ratio'])
        total_template_match_ratio.append(accuracy_dict['template_match_ratio'])
        total_llm_command_match_ratio.append(accuracy_dict['llm_command_match_ratio'])
        total_rule_command_match_ratio.append(accuracy_dict['rule_command_match_ratio'])

    average_command_match_ratio = sum(total_command_match_ratio) / len(total_command_match_ratio) if total_command_match_ratio else 0
    average_param_match_ratio = sum(total_param_match_ratio) / len(total_param_match_ratio) if total_param_match_ratio else 0
    average_template_match_ratio = sum(total_template_match_ratio) / len(total_template_match_ratio) if total_template_match_ratio else 0
    average_llm_command_match_ratio = sum(total_llm_command_match_ratio) / len(total_llm_command_match_ratio) if total_llm_command_match_ratio else 0
    average_rule_command_match_ratio = sum(total_rule_command_match_ratio) / len(total_rule_command_match_ratio) if total_rule_command_match_ratio else 0
    return {
        'average_command_match_ratio': average_command_match_ratio,
        'average_param_match_ratio': average_param_match_ratio,
        'average_template_match_ratio': average_template_match_ratio,
        'average_llm_command_match_ratio': average_llm_command_match_ratio,
        'average_rule_command_match_ratio': average_rule_command_match_ratio
    }


def cul_command_accuracy(translated_dir, real_dir, config_files):
    total_command_match_score = 0
    total_command_match_account = 0
    total_command_match_ratio = []
    for file_name in config_files:
        file_result = os.path.join(translated_dir, file_name)
        file_expected = os.path.join(real_dir, file_name)

        result_commands = parse_config_file_intact(file_result)
        expected_commands = parse_config_file_intact(file_expected)

        command_match_score, command_match_account, error_commands = calculate_match_ratio(result_commands,
                                                                                         expected_commands,
                                                                                         [],
                                                                                         [])
        command_match_ratio = command_match_score / command_match_account if command_match_account > 0 else 0
        total_command_match_ratio.append(command_match_ratio)
        # total_command_match_score += command_match_score
        # total_command_match_account += command_match_account

    # average_command_match_ratio = total_command_match_score / total_command_match_account if total_command_match_account > 0 else 0
    average_command_match_ratio = sum(total_command_match_ratio) / len(total_command_match_ratio) if total_command_match_ratio else 0
    return average_command_match_ratio

def cul_grammatical_accuracy(translated_dir, real_dir, config_files, config_model:{}):
    total_match_score = 0
    total_match_account = 0
    total_match_ratio = []
    for file_name in config_files:
        file_result = os.path.join(translated_dir, file_name)
        file_expected = os.path.join(real_dir, file_name)

        result_templates, result_extra_command = parse_config_file(file_result, config_model)
        expected_templates, expected_extra_command = parse_config_file(file_expected, config_model)

        match_score, match_account, error_templates = calculate_match_ratio(result_templates,
                                                                            expected_templates,
                                                                            result_extra_command,
                                                                            expected_extra_command)

        match_ratio = match_score / match_account if match_account > 0 else 0
        total_match_ratio.append(match_ratio)
        # total_match_score += match_score
        # total_match_account += match_account
    # average_match_ratio = total_match_score / total_match_account if total_match_account > 0 else 0
    average_match_ratio = sum(total_match_ratio) / len(total_match_ratio) if total_match_ratio else 0
    return average_match_ratio


def get_all_templates(data):
    templates = []

    def dfs(data:dict):
        for key, value in data.items():
            if isinstance(value, dict):
                dfs(value)
            elif key == 'template':
                templates.append(value)
    dfs(data)
    return templates

def cul_grammatical_accuracy_with_json(translated_dir, real_dir, config_files):
    '''
    直接使用保存的template和label对应的json文件进行匹配，不实用config_model
    real_dir="./exper_data/vendor/"
    '''

    total_match_score = 0
    total_match_account = 0
    for file_name in config_files:
        device_name= os.path.splitext(file_name)[0]

        trans_templates = json.load(open(os.path.join(translated_dir, f"{device_name}_temp.json")))
        expected_json = os.path.join(real_dir, f"{device_name}.json")
        expected_templates = get_all_templates(json.load(open(expected_json)))

        match_score, match_account, error_templates = calculate_match_ratio(trans_templates,
                                                                            expected_templates,
                                                                            [],
                                                                            [])
        total_match_score += match_score
        total_match_account += match_account
    average_match_ratio = total_match_score / total_match_account if total_match_account > 0 else 0
    return average_match_ratio

def cuL_llm_coverage_with_json(source_txt_dir,translated_dir, config_files):
    llm_command_accuracys = []
    for file_name in config_files:
        device_name= os.path.splitext(file_name)[0]
        source_config_txt = os.path.join(source_txt_dir, f"{device_name}.txt")
        source_commands = parse_config_file_intact(source_config_txt)

        evaluate_json = json.load(open(os.path.join(translated_dir, f"{device_name}_evaluate.json")))
        command_for_llm = evaluate_json['command_for_llm']
        llm_command_accuracy = len(command_for_llm) / len(source_commands) if len(source_commands) > 0 else 0
        llm_command_accuracys.append(llm_command_accuracy)
    average_match_ratio = sum(llm_command_accuracys) / len(llm_command_accuracys) if  llm_command_accuracys else 0
    return average_match_ratio

def cuL_llm_accuracy_with_json(translated_dir, config_files):
    llm_command_accuracys = []
    for file_name in config_files:
        device_name= os.path.splitext(file_name)[0]
        evaluate_json = json.load(open(os.path.join(translated_dir, f"{device_name}_evaluate.json")))
        llm_command_accuracy = evaluate_json['llm_command_accuracy']
        if llm_command_accuracy > 0:
            llm_command_accuracys.append(llm_command_accuracy)
    average_match_ratio = sum(llm_command_accuracys) / len(llm_command_accuracys) if  llm_command_accuracys else 0
    return average_match_ratio

def cul_device_grammatical_accuracy_with_json(translated_dir, real_dir, config_files):
    grammatical_accuracy = []  # 存储每个文件的准确率
    command_accuracy = []
    for file_name in config_files:
        device_name= os.path.splitext(file_name)[0]
        evaluate_json = json.load(open(os.path.join(translated_dir, f"{device_name}_evaluate.json")))

        grammatical_accuracy.append(evaluate_json['grammatical_accuracy'])
        command_accuracy.append(evaluate_json['command_accuracy'])
    # 计算所有文件的平均准确率
    average_grammatical_accuracy = sum(grammatical_accuracy) / len(grammatical_accuracy) if grammatical_accuracy else 0
    average_command_accuracy = sum(command_accuracy) / len(command_accuracy) if command_accuracy else 0
    return average_grammatical_accuracy, average_command_accuracy

def grammatical_match(device_name, match_rule, real_dir):
    expected_json = os.path.join(real_dir, f"{device_name}.json")
    expected_templates = get_all_templates(json.load(open(expected_json)))

    error_mapping_rules = defaultdict(set)
    error_mapping_rules_count = defaultdict(int)

    for map_rule_str in match_rule.keys():
        match_rule = ast.literal_eval(map_rule_str)
        target_template_matchs = match_rule[1]
        if isinstance(target_template_matchs[0], list):
            for target_match in target_template_matchs:
                if target_match[2] not in expected_templates:
                    error_mapping_rules[match_rule[0]].add(target_match[2])
                    error_mapping_rules_count[match_rule[0]] += 1
        else:
            if target_template_matchs[0] == '':
                continue
            if target_template_matchs[0] not in expected_templates:
                error_mapping_rules[match_rule[0]].add(target_template_matchs[0])
                error_mapping_rules_count[match_rule[0]] += 1
    return error_mapping_rules, error_mapping_rules_count



def calculate_param_match_ratio(result_templates:{}, expected_templates:{}, result_extra_commands:[], expected_extra_commands:[]):
    """计算翻译的模板序列的匹配度"""
    match_score = 0
    match_count = 0

    for result_template, result_commands in result_templates.items():
        if result_template in expected_templates:
            for result_command in result_commands:
                if result_command in expected_templates[result_template]:
                    match_score += 1
                match_count += 1

    for result_extra_command in result_extra_commands:
        if result_extra_command in expected_extra_commands:
            match_count += 1
            match_score += 1

    return match_score, match_count

def cul_param_accuracy(translated_dir, real_dir, config_files, config_model: {}):
    def parse_config_file(file_path, config_model):
        """解析配置文件为模板序列"""
        templates = defaultdict(list)
        extra_commands = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # 去除前后空格和缩进
                command = line.strip()
                if command:
                    template = find_template(command, config_model)
                    if template:
                        templates[template.lower()].append(command.lower())
                    else:
                        extra_commands.append(command.lower())
        return templates, extra_commands

    total_match_score = 0
    total_match_ccount = 0
    for file_name in config_files:
        file_result = os.path.join(translated_dir, file_name)
        file_expected = os.path.join(real_dir, file_name)

        result_templates, result_extra_command = parse_config_file(file_result, config_model)
        expected_templates, expected_extra_command = parse_config_file(file_expected, config_model)

        match_score, match_ccount = calculate_param_match_ratio(result_templates,
                                                                            expected_templates,
                                                                            result_extra_command,
                                                                            expected_extra_command)
        total_match_score += match_score
        total_match_ccount += match_ccount
    average_match_ratio = total_match_score / total_match_ccount if total_match_ccount > 0 else 0
    return average_match_ratio

if __name__ == '__main__':
    scale = 2000
    vendors = ['Juniper']
    translated_config_base = './exper_data/translated_config'

    for source_vendor in ['Cisco']:
        for target_vendor in ['Juniper']:
            if target_vendor == source_vendor:
                continue

            translated_config_dir = os.path.join(translated_config_base, str(scale), source_vendor, target_vendor)
            trannlated_config_files = [f for f in os.listdir(translated_config_dir) if f.endswith('.txt')]
            real_config_dir = f'./exper_data/label/{target_vendor}'
            # config_model = f'../dataset_multi_vendor_config/config_model/different_scale/{target_vendor}_{scale}.json'
            config_model = f'../dataset_multi_vendor_config/config_model/different_scale/{target_vendor}_{scale}.json'
            config_model = load_config_model(config_model)

            command_accuracy = cul_command_accuracy(translated_config_dir, real_config_dir, trannlated_config_files)
            print(command_accuracy)

'''
Average Match Ratio: 0.67
Average intact Match Ratio: 0.64
'''
