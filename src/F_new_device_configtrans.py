# 从json解析配置到目标供应商配置
import sys

from experiment.tree_match import parse_config_file_content_intact

sys.path.append("/data/public/hrx/Repositories/config_trans")
import os
import types
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import json
from langchain_community.embeddings import HuggingFaceEmbeddings
import numpy as np
import torch
import warnings
import re
from src.D_Command_node import CommandNode  # parse_command_node, build_command_node
from src.E_command_match import ConfigMatcher

warnings.filterwarnings("ignore", category=UserWarning, module="torch")

# 指定设备
device = "cuda:0"  # 使用GPU 1
project_root = Path(__file__).parent.parent


# 同阶段3的insert_template
# insert 'template' item into juniper config model
def insert_template(config_model: dict) -> dict:
    for k, sub_dict in config_model.items():
        # 若子项不是 dict，可能是其他值，跳过（通常不应该出现，但做个保护）
        if not isinstance(sub_dict, dict):
            continue

        # 拿到该节点的 template，作为新 key
        template_key = sub_dict.get("template")
        if not template_key:
            # 没有 template 就插入
            sub_dict["template"] = k

        for child_k, child_v in sub_dict.items():
            insert_template({child_k: child_v})

    return config_model


# 拆分出配置命令节点（不同于阶段4中，未做文本嵌入）
def build_command_node(Command_nodes: dict, config_model: dict):
    for key in config_model.keys():
        # 初始化模块
        Command_nodes[key] = {}
        # 建立根节点向量
        # 首先是结构特征（包括depth/param_signature(count/order)/parent_command）
        command_parameters = config_model[key]["parameters"] if config_model[key].get("parameters") else {}
        structural_feature = {'depth': 0,
                              'params': command_parameters,
                              'parent_command': []}
        # 其次为语义特征（包括template/command/explanation/parameters）
        command_example = config_model[key]["command"] if config_model[key].get("command") else ''
        command_explanation = config_model[key]["explanation"] if config_model[key].get("explanation") else ''
        semantic_feature = {'template': config_model[key]['template'],
                            'command': command_example,
                            'explanation': command_explanation,
                            'parameters': command_parameters}
        Command_nodes[key][key] = {'structural_features': structural_feature,
                                   'semantic_features': semantic_feature}
        # 解析子树中的所有命令节点，行程模块
        parse_command_node(Command_nodes[key], config_model[key], parent_command=[key], depth=1)

    return Command_nodes


def parse_command_node(Command_nodes: dict, config_model: dict, parent_command=[], depth=0):
    # print(parent_command)
    for k, sub_dict in config_model.items():
        if not isinstance(sub_dict, dict):
            continue

        template_key = sub_dict.get("template")
        command_key = sub_dict.get("command")
        explanation_key = sub_dict.get("explanation")
        if not template_key:  # or not command_key or not explanation_key:
            # 没有 template/command/explanation 就跳过, 要保证配置命令语义/结构的完整性
            continue
        else:
            # 逐个解析每个命令节点的数据项
            # 首先是结构特征（包括depth/param_signature(count/order)/parent_command）
            command_parameters = sub_dict["parameters"] if sub_dict.get("parameters") else {}
            structural_feature = {'depth': depth,
                                  'params': command_parameters,
                                  'parent_command': parent_command}
            # 其次为语义特征（包括template/command/explanation/parameters）
            command_example = sub_dict["command"] if sub_dict.get("command") else ''
            command_explanation = sub_dict["explanation"] if sub_dict.get("explanation") else ''
            semantic_feature = {'template': sub_dict['template'],
                                'command': command_example,
                                'explanation': command_explanation,
                                'parameters': command_parameters}

            if not sub_dict.get(k):
                Command_nodes[k] = {'structural_features': structural_feature,
                                    'semantic_features': semantic_feature}

        parse_command_node(Command_nodes, sub_dict, parent_command + [str(k)], depth + 1)
    return Command_nodes


# 设备配置翻译器
class Config_Translater:

    def __init__(self, mapping_libraries, config_matchers, translation_llm,
                 embedding_model, config_models={}):
        self.mapping_libraries = mapping_libraries  # 加载配置模板映射规则库
        self.config_matchers = config_matchers  # 加载配置命令匹配器
        self.translation_llm = translation_llm  # 加载配置翻译模型
        self.embedding_model = embedding_model  # 加载嵌入模型
        self.config_models = config_models  # 加载配置模型
        # 初始化配置命令匹配器
        # self.config_matchers = self.initialize_config_matchers(target_command_templates)
        self.node_id = 0

    '''
    def initialize_config_matchers(self, target_command_templates):
        self.config_matchers = {}
        for vendor, target_command_template in target_command_templates.items():
            self.config_matchers[vendor] = ConfigMatcher(target_command_template)
    '''

    # 进行配置翻译
    def translation(self, json_configuration, vendor, target_vendor, tau=0.65, source_total_config=None):
        config_match = []  # 保存翻译（匹配）集合
        # 给juniper配置模型加个保险
        if vendor == 'Juniper':
            json_configuration = insert_template(json_configuration)
        commands_feature = {}  # 分拆每一条配置命令特征
        commands_feature = build_command_node(commands_feature, json_configuration)

        # 阶段一：规则映射rule_mapping, rest_commands_feature是在映射库中不存在的配置命令
        rest_commands_feature, config_match = self.rule_mapping(commands_feature,
                                                                config_match, vendor, target_vendor)

        # 阶段二：模糊映射fuzzy_mapping-->针对规则映射库未覆盖的配置命令
        config_match = self.fuzzy_mapping(rest_commands_feature, config_match, vendor, target_vendor, tau=tau,
                                          source_total_config=source_total_config)

        map_rule_freq = {}
        for command, match in config_match:
            map_rule = str([match['template'], match['match']])

            if map_rule not in map_rule_freq.keys():
                map_rule_freq[map_rule] = 1
            else:
                map_rule_freq[map_rule] += 1

        # 阶段四：配置命令编排，配置参数直接填充
        arranged_config = self.config_arranging(config_match, target_vendor)
        # print(json.dumps(arranged_config, indent=4, ensure_ascii=False))

        # 阶段五：llm配置参数映射与修正
        # target_config = self.parameter_mapping_with_LLM_rewrite(arranged_config, vendor, target_vendor)
        target_config = self.parameter_mapping_with_LLM_remapping(arranged_config, vendor, target_vendor)

        # 阶段六：输出并保存翻译的配置命令
        trans_res_dict = self.print_and_save_translation_config(target_config,
                                                                target_vendor)

        return {
            'trans_res': trans_res_dict['trans_res'],
            'trans_mapping_info': trans_res_dict['trans_mapping_info'],
            'trans_templates': trans_res_dict['trans_templates'],
            'map_rule_freq': map_rule_freq,
            'llm_transd_commands': trans_res_dict['llm_transd_commands'],
            'command_for_llm': trans_res_dict['command_for_llm'],
            'llm_origin_response': trans_res_dict['llm_origin_response'],
            'source_commands': trans_res_dict['source_commands'],
        }

    def translation_without_llm(self, json_configuration, vendor, target_vendor, istatistics=False, tau=0.9):
        '''
        启发式翻译
        '''
        config_match = []  # 保存翻译（匹配）集合
        # 给juniper配置模型加个保险
        if vendor == 'Juniper':
            json_configuration = insert_template(json_configuration)
        commands_feature = {}  # 分拆每一条配置命令特征
        commands_feature = build_command_node(commands_feature, json_configuration)

        # 阶段一：规则映射rule_mapping, rest_commands_feature是在映射库中不存在的配置命令
        rest_commands_feature, config_match = self.rule_mapping(commands_feature,
                                                                config_match, vendor, target_vendor)
        # print(f"rest_commands_feature: {rest_commands_feature}", '\n', config_match)
        # print(json.dumps(config_match, indent=2, ensure_ascii=False))
        if not istatistics:
            # 阶段二：模糊映射fuzzy_mapping-->针对规则映射库未覆盖的配置命令
            # if len(rest_commands_feature) > 0:
            #     config_match = self.fuzzy_mapping(rest_commands_feature, config_match, vendor, target_vendor, tau=0)
            # print(f"config_match: {json.dumps(config_match, indent=2, ensure_ascii=False)}")
            # 映射规则使用统计
            map_rule_freq = {}
            for command, match in config_match:
                map_rule = str([match['template'], match['match']])

                if map_rule not in map_rule_freq.keys():
                    map_rule_freq[map_rule] = 1
                else:
                    map_rule_freq[map_rule] += 1
            # print(f"map_rule_freq: {map_rule_freq}")
            # 阶段四：配置命令编排，配置参数直接填充
            arranged_config = self.config_arranging(config_match, target_vendor)
            # print(json.dumps(arranged_config, indent=2, ensure_ascii=False))

            # 阶段五：参数映射
            target_config = self.parameter_mapping_with_LLM_remapping(arranged_config, vendor, target_vendor)

            # 阶段六：输出并保存翻译的配置命令
            trans_res_dict = self.print_and_save_translation_config(target_config,
                                                                    target_vendor)

            return {
                'trans_res': trans_res_dict['trans_res'],
                'trans_mapping_info': trans_res_dict['trans_mapping_info'],
                'trans_templates': trans_res_dict['trans_templates'],
                'map_rule_freq': map_rule_freq,
                'llm_transd_commands': trans_res_dict['llm_transd_commands'],
                'command_for_llm': trans_res_dict['command_for_llm'],
                'llm_origin_response': trans_res_dict['llm_origin_response'],
                'source_commands': trans_res_dict['source_commands'],
            }
        else:
            statistic_data = {
                "command_count": len(rest_commands_feature) + len(config_match),
                "rule_ccount": len(config_match),
                "llm_ccount": 0
            }
            map_rule_freq = {}
            for command, match in config_match:
                map_rule = str([match['template'], match['match']])

                if map_rule not in map_rule_freq.keys():
                    map_rule_freq[map_rule] = 1
                else:
                    map_rule_freq[map_rule] += 1
            _, filtered_commands_feature = self.fuzzy_mapping_for_statistic(rest_commands_feature, config_match, vendor,
                                                                            target_vendor, tau=tau)
            statistic_data['llm_ccount'] = len(filtered_commands_feature)
            return statistic_data, map_rule_freq

    # 阶段一借助模板映射库实现规则映射
    def rule_mapping(self, commands_feature, config_match, vendor, target_vendor):
        rest_commands_feature = []  # 保存不包含在规则映射库中的配置命令
        specific_mapping_library = self.mapping_libraries['{}_{}'.format(vendor, target_vendor)]
        # 查找每一条配置在规则库里的映射关系
        for key in commands_feature.keys():
            for command, feature in commands_feature[key].items():
                # 不在配置映射库中
                template = feature['semantic_features']['template']
                if template not in specific_mapping_library.keys():
                    # print(template)
                    rest_commands_feature.append(
                        (command, {'feature': feature, 'root': key, 'root_feature': commands_feature[key][key]}))

                    continue
                # 在映射库中的配置命令
                config_match.append(
                    (command, {'template': template, 'match': specific_mapping_library[template], 'root': key}))

        return rest_commands_feature, config_match

    # 阶段二借助目标供应商配置模板基于语义相似度实现模糊映射
    def fuzzy_mapping(self, rest_commands_feature, config_match, vendor, target_vendor, tau=0.65,
                      source_total_config=None):
        # 根据语义做模糊匹配
        for command, features in rest_commands_feature:
            # structural_feature = features['feature']['structural_feature']
            # semantic_feature = features['feature']['semantic_feature']
            # 创建命令节点，执行语义/参数嵌入
            Command_Node = CommandNode(features['feature']['structural_features'],
                                       features['feature']['semantic_features'], self.embedding_model)
            command_node = {'structural_features': Command_Node.structural_features,
                            'semantic_features': Command_Node.semantic_features,
                            'parameter_features': Command_Node.paras_semantic_features}
            # src_root, src_root_semantic留个接口，后面补上
            Root_Node = CommandNode(features['root_feature']['structural_features'],
                                    features['root_feature']['semantic_features'], self.embedding_model)
            root_node = {'structural_features': Root_Node.structural_features,
                         'semantic_features': Root_Node.semantic_features,
                         'parameter_features': Root_Node.paras_semantic_features}
            root_semantic = torch.tensor(root_node['semantic_features'], dtype=torch.float32).unsqueeze(0).cuda()
            src_root = features['root']
            matched_result, best_root, match_score = self.config_matchers[target_vendor].find_best_match(vendor,
                                                                                                         command_node,
                                                                                                         src_root,
                                                                                                         root_semantic)
            if match_score > tau:  # 匹配度大于阈值
                template = features['feature']['semantic_features']['template']
                # 补充现有的模板库
                self.mapping_libraries['{}_{}'.format(vendor, target_vendor)][template] = matched_result
            else:
                matched_result = self.translation_llm.llm_command_mapping(command, vendor,
                                                                          target_vendor,
                                                                          source_total_config)  # matched_result = str
                if not matched_result:
                    template = features['feature']['semantic_features']['template']
                    # 补充现有的模板库
                    self.mapping_libraries['{}_{}'.format(vendor, target_vendor)][template] = matched_result
                else:
                    for match in matched_result:
                        result_node = {
                            "structural_features": {
                                "context_topology": {
                                    "parent_command": []
                                },
                                "param_signature": {
                                    "count": 0,
                                    "order": []
                                },
                                "command_depth": 0
                            },
                        }
                        if match['trans_command'] not in self.config_matchers[target_vendor].templates.keys():
                            self.config_matchers[target_vendor].templates[match['trans_command']] = {
                                match['trans_command']: result_node}

            template = features['feature']['semantic_features']['template']
            config_match.append((command, {'template': template, 'match': matched_result, 'root': src_root}))

        return config_match

    def fuzzy_mapping_for_statistic(self, rest_commands_feature, config_match, vendor, target_vendor, tau=0.65):
        # 根据语义做模糊匹配
        filtered_commands_feature = []
        for command, features in rest_commands_feature:
            # 创建命令节点，执行语义/参数嵌入
            Command_Node = CommandNode(features['feature']['structural_features'],
                                       features['feature']['semantic_features'], self.embedding_model)
            command_node = {'structural_features': Command_Node.structural_features,
                            'semantic_features': Command_Node.semantic_features,
                            'parameter_features': Command_Node.paras_semantic_features}
            # src_root, src_root_semantic留个接口，后面补上
            Root_Node = CommandNode(features['root_feature']['structural_features'],
                                    features['root_feature']['semantic_features'], self.embedding_model)
            root_node = {'structural_features': Root_Node.structural_features,
                         'semantic_features': Root_Node.semantic_features,
                         'parameter_features': Root_Node.paras_semantic_features}
            root_semantic = torch.tensor(root_node['semantic_features'], dtype=torch.float32).unsqueeze(0).cuda()
            src_root = features['root']
            matched_result, best_root, match_score = self.config_matchers[target_vendor].find_best_match(vendor,
                                                                                                         command_node,
                                                                                                         src_root,
                                                                                                         root_semantic)
            if match_score <= tau:  # 匹配度大于阈值
                filtered_commands_feature.append(command)

        return [], filtered_commands_feature

    # 阶段三使用大模型做配置映射，保留接口，当前翻译流程关注前两阶段效果
    def LLMmodel_mapping(self, rest_commands_feature, config_match, vendor, target_vendor):
        raise NotImplementedError

    # 阶段四进行配置编排，对应正确的视图
    def config_arranging(self, config_matches, target_vendor):
        arranged_command = []
        # Juniper没有视图层级, 按顺序输出配置命令即可
        for item_k, item_v in config_matches:
            # 依据翻译命令的视图深度实现编排{0:{c0:[4,[0,0,1,1]]}}
            # paras-->具体配置参数值, depth-->第零层, translated_command-->命令模板, 
            # para_num-->参数数量, para_placeholders-->[0,0,1,1]参数填充占位标识,
            # para_match --> 参数映射,  target_command--> 最终翻译命令
            paras = self.para_extract(item_k, item_v['template'])
            # any(len(paras) <= match['para_map'][0] for match in item_v['match'] if len(match['para_map'])>0)
            arranged_command_item = {'para': paras}
            arranged_command.append((item_k, arranged_command_item))
            # 如果是list需要遍历整合信息
            # if isinstance(item_v['match'], list):
            for para_match in item_v['match']:  # 遍历每一个参数映射信息
                # 查找翻译命令的视图层级
                '''if para_match[''] == 4:
                    translated_command = para_match[2]  # 翻译的配置命令
                elif len(para_match) == 2:
                    translated_command = para_match[0]
                else:
                    raise ValueError("para_match length error")
                # 配置命令节点'''
                translated_command = para_match['trans_command']
                root = para_match['root']
                try:
                    command_node = self.config_matchers[target_vendor].templates[root][
                        translated_command]  # 至少这这前面的不能随便改
                except KeyError:
                    print(f"KeyError: {translated_command}")
                    continue
                # 命令视图层级
                depth = command_node['structural_features']['command_depth']
                # 参数数量
                para_num = command_node['structural_features']['param_signature']['count']
                parent_commands = para_match['parent_command']
                # 如果不包含该层级
                if depth not in arranged_command_item.keys():
                    para_placeholders = [0] if para_num == 0 else [
                                                                      0] * para_num  # 为什么每一个参数映射信息都要有一个站位符呢？而且站位符的长度是目标命令的参数数量？
                    if para_match['para_map']:
                        if not -1 in para_match:
                            try:
                                para_placeholders[para_match['para_map'][1]] = 1  # ==1表示目标命令的该位置被映射到了
                            except IndexError:
                                print(f"IndexError: para_placeholders index out of range: {para_match}")
                    # print(paras, para_num, item_v['match'], translated_command)
                    arranged_command_item[depth] = {translated_command:
                                                        {'para_num': para_num,
                                                         'para_placeholders': para_placeholders,
                                                         'para_match': self.match_and_extract(paras, para_num,
                                                                                              item_v['match'],
                                                                                              translated_command),
                                                         'target_command': translated_command,
                                                         'parent_node': parent_commands,
                                                         'source': 'llm' if 'source' in para_match.keys() else 'rule',
                                                         'origin_response': para_match[
                                                             'origin_response'] if 'origin_response' in para_match.keys() else ''
                                                         }
                                                    }
                # 如果该层级中不包含这一配置命令
                elif translated_command not in arranged_command_item[depth].keys():
                    # 参数填充占位符
                    para_placeholders = [0] if para_num == 0 else [0] * para_num
                    if para_match['para_map']:
                        if not -1 in para_match:
                            try:
                                para_placeholders[para_match['para_map'][1]] = 1
                            except IndexError:
                                print(f"IndexError: para_placeholders index out of range: {para_match}")
                    arranged_command_item[depth].update({translated_command:
                                                             {'para_num': para_num,
                                                              'para_placeholders': para_placeholders,
                                                              'para_match': self.match_and_extract(paras,
                                                                                                   para_num,
                                                                                                   item_v[
                                                                                                       'match'],
                                                                                                   translated_command),
                                                              'target_command': translated_command,
                                                              'parent_node': parent_commands,
                                                              'source': 'llm' if 'source' in para_match.keys() else 'rule',
                                                              'origin_response': para_match[
                                                                  'origin_response'] if 'origin_response' in para_match.keys() else ''
                                                              }
                                                         })
                # 如果该层级包含这一配置命令
                else:
                    if para_match['para_map']:
                        if not -1 in para_match:
                            try:
                                arranged_command_item[depth][translated_command]['para_placeholders'][
                                    para_match['para_map'][1]] = 1
                            except IndexError:
                                print(f"IndexError: para_placeholders index out of range: {para_match}")
            # 都是list，没参数的只有两项，命令和父命令
            '''else:
                # 查找翻译命令的视图层级
                translated_command = item_v['match']['trans_command']  # 纠正错误
                if not translated_command: # 空字符
                    continue
                # 配置命令节点
                try:
                    command_node = self.config_matchers[target_vendor].templates[translated_command]  # 至少这这前面的不能随便改
                except KeyError:
                    print(f"KeyError: {translated_command}")
                    continue
                # 命令视图层级
                depth = command_node['structural_features']['command_depth']
                # 参数数量
                para_num = command_node['structural_features']['param_signature'].get('count', 0)
                # 参数填充占位符
                para_placeholders = [0] if para_num == 0 else [0] * para_num
                parent_commands = item_v['match'][-1]
                arranged_command[item_k][depth] = {translated_command:
                                                       {'para_num': para_num,
                                                        'para_placeholders': para_placeholders,
                                                        'para_match': self.match_and_extract(paras, para_num,
                                                                                             item_v['match'],
                                                                                             translated_command),
                                                        'target_command': translated_command,
                                                        'parent_node': parent_commands}
                                                   }'''
        return arranged_command

    def parameter_mapping_with_LLM_remapping(self, arranged_config: dict, vendor, target_vendor) -> dict:
        target_commands = {}  # 最终配置命令
        # 遍历每一个需要翻译的配置命令
        for index, (src_command, translation) in enumerate(arranged_config):
            all_params = translation['para']
            # 遍历该需要翻译配置命令中每一层级的配置命令
            for depth, translation_commands in translation.items():
                # 不是字典跳过，包含非翻译命令的信息
                if not isinstance(translation_commands, dict):
                    continue
                # 基于配置参数合并配置命令模板
                for command, command_v in translation_commands.items():
                    parent_commands = command_v['parent_node']
                    if len(parent_commands) > 0:  # 不是根节点
                        self.insert_parent_command(target_commands, index, src_command, int(depth), parent_commands,
                                                   all_params, target_vendor)  # 补充父节点
                    target_commands = self.command_param_merge(target_commands, index, src_command,
                                                               int(depth), command, command_v)

        # 参数插入配置命令模板
        # 创建一个线程池，将llm映射的任务提交给线程池
        with ThreadPoolExecutor() as executor:
            futures = []
            for id, (src_command, translation) in target_commands.items():
                # 遍历该需要翻译配置命令中每一层级的配置命令
                for depth, translation_commands in translation.items():
                    if depth == -1:
                        continue
                    # 基于配置参数插入配置命令模板
                    for command, command_v in translation_commands.items():
                        # 使用llm进行参数映射修复
                        if command_v['para_num'] > 0:
                            future = executor.submit(
                                self.translation_llm.param_map_repair,
                                target_vendor,
                                command_v
                            )
                            futures.append((command_v, future))
            # 获取结果并更新
            for command_v, future in futures:
                llm_target_command = future.result()
                if llm_target_command != '':
                    command_v['target_command'] = self.para_fill(llm_target_command['para_match'],
                                                                 llm_target_command['target_command'])


        return target_commands

    def parameter_mapping(self, arranged_config: dict, vendor, target_vendor) -> dict:
        target_commands = {}  # 最终配置命令
        # 遍历每一个需要翻译的配置命令
        for src_command, translation in arranged_config.items():
            all_params = translation['para']
            # 遍历该需要翻译配置命令中每一层级的配置命令
            for depth, translation_commands in translation.items():
                # 不是字典跳过，包含非翻译命令的信息
                if not isinstance(translation_commands, dict):
                    continue
                # 基于配置参数合并配置命令模板
                for command, command_v in translation_commands.items():
                    parent_commands = command_v['parent_node']
                    if len(parent_commands) > 0:  # 不是根节点
                        self.insert_parent_command(target_commands, src_command, int(depth), parent_commands,
                                                   all_params, target_vendor)  # 补充父节点
                    target_commands = self.command_param_merge(target_commands, src_command,
                                                               int(depth), command, command_v)
        # print(f"target_commands: {target_commands}")
        # 参数插入配置命令模板
        for src_command, translation in target_commands.items():
            # 遍历该需要翻译配置命令中每一层级的配置命令
            for depth, translation_commands in translation.items():
                if depth == -1:
                    continue
                for command, command_v in translation_commands.items():
                    command_v['target_command'] = self.para_fill(command_v['para_match'],
                                                                 command_v['target_command'])
        return target_commands

    # 基于配置参数合并配置命令模板(带翻译的配置命令参数分布在多个命令中，并包含共享的命令)
    def command_param_merge(self, target_commands: dict, src_command_id, src_command: str, src_depth: int,
                            command: str, command_info: dict) -> dict:
        # merge标识符
        merged_flag = 0
        # 遍历是否存在与command相同的命令
        for id, (pre_src_command, translation) in target_commands.items():  # 变量名重复，已改
            for depth, translation_commands in translation.items():
                for command_k, command_v in translation_commands.items():
                    # 若有相同的配置命令模板
                    if command_k == command:
                        # 可合并-->[1, 1, 0, 0] + [0, 0, 1, 1] = [1,1,1,1]
                        try:
                            merged_placeholders = np.array(command_v['para_placeholders']) | np.array(
                                command_info['para_placeholders'])
                        except Exception as e:
                            continue
                        if not np.array_equal(merged_placeholders, np.array(command_v['para_placeholders'])):
                            # 将参数填补到可合并配置命令中
                            # 使用列表推导式，优先选择非空元素
                            pre_merged_paras = [x if x != 'none' else y for x, y in
                                                zip(command_v['para_match'], command_info['para_match'])]
                            command_v['para_placeholders'] = merged_placeholders.tolist()
                            command_v['para_match'] = pre_merged_paras

                            this_merged_paras = [x if x != 'none' else y for x, y in
                                                 zip(command_info['para_match'], command_v['para_match'])]
                            command_info['para_placeholders'] = merged_placeholders.tolist()
                            command_info['para_match'] = this_merged_paras
                            merged_flag = 1
        if merged_flag == 0:
            target_commands.setdefault(src_command_id, (src_command, {}))[1].setdefault(src_depth, {})[
                command] = command_info
        return target_commands

    """
    匹配并提取符合条件的项的前两个值
    :para_match: 输入的数据结构
    :return: 符合条件的项的 [a, b] 列表
    """

    def match_and_extract(self, paras: list, para_num: int,
                          para_match: list, target_template: str) -> list:
        result = ['none'] * para_num
        if para_num > 0:
            for item in para_match:
                # 检查最后一项是否匹配目标模板
                if item['trans_command'] == target_template and item['para_map']:
                    try:
                        result[item['para_map'][1]] = paras[item['para_map'][0]]
                    except Exception as e:
                        print(para_match)
                        continue
        return result

    """
    从源命令中提取参数并填充到目标模板中
    :param src_cmd: 源命令，如 "hostname Hub"
    :param src_template: 源模板，如 "hostname [parameter1]"
    :param dest_template: 目标模板，如 "sysname [parameter1]"
    :return: 填充后的目标命令
    """

    def para_extract(self, src_cmd: str, src_template: str) -> str:
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

    def para_fill(self, params: list, dest_template: str) -> str:
        # 填充到目标模板
        if isinstance(params, types.GenericAlias):
            return dest_template
        para_placeholders = re.findall(r'\[parameter\d+\]', dest_template)
        for index, param in enumerate(params):
            if index >= len(para_placeholders):
                break
            # dest_template = dest_template.replace(f"[parameter{index + 1}]", '{' + param + '}')
            dest_template = dest_template.replace(f"{para_placeholders[index]}", str(param))
        return dest_template

    def merge_config_nodes(self, root, target_vendor):
        merged_root = ConfigNode("system", "", root.id[0])
        node_map = {}

        for child in root.children:
            key = child.line
            if key not in node_map:
                node_map[key] = deepcopy(child)
                merged_root.add_child(node_map[key])
            else:
                node_map[key].merge(child)

        return merged_root

    def merge_mapping_pairs(self, pairs):
        merged_pairs = {}
        for pair in pairs:
            source_cmd = pair[0]
            if source_cmd not in merged_pairs:
                merged_pairs[source_cmd] = [(pair[1], pair[2])]
            else:
                merged_pairs[source_cmd].append((pair[1], pair[2]))
        return merged_pairs

    def get_next_node_id(self):
        """获取下一个 node_id 并自动加一"""
        current_id = self.node_id
        self.node_id += 1
        return current_id

    # 输出对应视图的配置命令
    def print_and_save_translation_config(self, target_config, target_vendor):
        # print('target_config:', target_config)
        trans_pairs = []
        # 使用 get_next_node_id 方法获取 node_id
        root = ConfigNode("system", "", self.get_next_node_id())
        stack = [(root, -1)]
        llm_transd_commands = []
        source_commands = set()
        command_for_llm = set()
        llm_origin_response = set()
        # 遍历每一个需要翻译的配置命令
        for id, (command, translation) in target_config.items():
            # 遍历该需要翻译配置命令中每一层级的配置命令
            for depth, target_command in translation.items():
                if depth == -1:
                    continue
                # 输出该层级下所有的配置命令
                for target_temp, command_info in target_command.items():
                    node_id = self.get_next_node_id()
                    line = command_info['target_command']
                    source = command_info['source']
                    if source == 'llm':
                        temp = self.find_command_template(target_vendor, line)
                        llm_transd_commands.append([line, temp])  # 0: command , 1: template
                        command_for_llm.add(command)
                        llm_origin_response.add(command_info['origin_response'])
                    else:
                        temp = target_temp
                    source_commands.add(command)
                    # 使用 get_next_node_id 方法获取 node_id
                    node = ConfigNode(line, temp, node_id, source)
                    while stack and stack[-1][1] >= depth:
                        stack.pop()

                    stack[-1][0].add_child(node)
                    stack.append((node, depth))

                    trans_pairs.append((command, node_id, source))

        merged_mapping_pair = self.merge_mapping_pairs(trans_pairs)
        merged_config_tree = self.merge_config_nodes(root, target_vendor)

        if target_vendor == 'Juniper':
            trans_res = self.juniper_combine(merged_config_tree)
            trans_templates = self.juniper_template_combine(target_config)
            mapping_info = self.get_mapping_info(merged_config_tree, merged_mapping_pair, is_juniper=True)
        else:
            trans_res = "\n".join(merged_config_tree.to_lines()[1:])
            trans_templates = merged_config_tree.get_all_tags()
            mapping_info = self.get_mapping_info(merged_config_tree, merged_mapping_pair)

        # return trans_res, trans_mapping_info, trans_templates
        return {
            'trans_res': trans_res,
            'trans_mapping_info': mapping_info,
            'trans_templates': trans_templates,
            'command_for_llm': list(command_for_llm),
            'llm_transd_commands': llm_transd_commands,
            'llm_origin_response': list(llm_origin_response),
            'source_commands': list(source_commands)
        }

    def get_mapping_info(self, merged_config_tree, trans_pairs, is_juniper=False):
        source_cmds = []
        target_cmds = []
        edges = []
        source_id = 1
        if not is_juniper:
            target_cmd_info = merged_config_tree.to_mapping_graph()[1:]
            for target_cmd, ids, source in target_cmd_info:
                target_cmds.append({
                    "id": f't{ids[0]}',
                    "text": target_cmd,
                    "description": '',
                    "type": source
                })

            for source_cmd, mappings in trans_pairs.items():
                source_cmds.append({
                    "id": f's{source_id}',
                    "text": source_cmd,
                    "description": '',
                    "type": 'rule'
                })
                for target_id, _ in mappings:
                    for target_cmd, ids,_  in target_cmd_info:
                        if target_id in ids:
                            edges.append({
                                "source": f's{source_id}',
                                "target": f't{ids[0]}',
                            })
                            break
                source_id += 1
        else:
            if merged_config_tree.line == "system":
                subtrees = merged_config_tree.children
            else:
                subtrees = [merged_config_tree]
            commands = []

            def dfs(node, current_path, current_ids):
                current_path.append(node.line)
                current_ids.extend(node.id)
                # 如果是叶节点，将当前路径拼接为命令
                if not node.children:
                    commands.append(" ".join(current_path))
                    target_cmds.append({
                        "id": f't{current_ids[-1]}',
                        "ids": current_ids,
                        "text": " ".join(current_path),
                        "description": '',
                        "type": node.source
                    })
                # 递归遍历子节点
                for child in node.children:
                    dfs(child, current_path.copy(), current_ids.copy())  # 使用copy创建新的路径副本

            for subtree in subtrees:
                dfs(subtree, [], [])

            for source_cmd, mappings in trans_pairs.items():
                source_cmds.append({
                    "id": f's{source_id}',
                    "text": source_cmd,
                    "description": '',
                    "type": 'rule'
                })
                for target_id, _ in mappings:
                    for target_cmd_node in target_cmds:
                        if target_id in target_cmd_node['ids']:
                            edges.append({
                                "source": f's{source_id}',
                                "target": target_cmd_node['id']
                            }),
                            break
                source_id += 1

        # 对edges去重
        seen = set()
        unique_edges = []
        for edge in edges:
            hashable_edge = tuple(sorted(edge.items()))
            if hashable_edge not in seen:
                seen.add(hashable_edge)
                unique_edges.append(edge)

        return {
            "source_cmds": source_cmds,
            "target_cmds": target_cmds,
            "edges": unique_edges
        }


    def find_command_template(self, target_vendor, command):
        def _find_template(command, config_model):
            """递归查找命令对应的模板"""
            for template, details in config_model.items():
                # 递归查找子命令
                if isinstance(details, dict) and 'template' in details:
                    sub_template = _find_template(command, details)
                    if sub_template:
                        return sub_template

                # 使用正则表达式匹配模板
                if template == 'template':
                    pattern = re.sub(r"\[[^\]]+\]", r'(\\S+)', details)
                    pattern = f'^{pattern}$'
                    try:
                        if re.match(pattern, command):
                            return details
                        else:
                            continue
                    except re.error:
                        continue

            return None

        if target_vendor == 'Juniper':
            temp = _find_template(command, self.config_models['conbined_Juniper'])
            return temp if temp else command
        else:
            temp = _find_template(command, self.config_models[target_vendor])
            return temp if temp else command

    def juniper_combine(self, root):
        # 去除根节点，将树拆分为n个子树，深度遍历每个子树至根节点，将其line值用' '拼接为一条命令
        if root.line == "system":
            subtrees = root.children
        else:
            subtrees = [root]
        commands = []

        def dfs(node, current_path):
            current_path.append(node.line)
            # 如果是叶节点，将当前路径拼接为命令
            if not node.children:
                commands.append(" ".join(current_path))
            # 递归遍历子节点
            for child in node.children:
                dfs(child, current_path.copy())  # 使用copy创建新的路径副本

        for subtree in subtrees:
            dfs(subtree, [])

        trans_res = '\n'.join(commands)
        return trans_res

    # juniper模板合并
    def juniper_template_combine(self, target_config):
        trans_templates = []
        for id, (src_command, translation) in target_config.items():
            comamnd_key = list(translation.keys())[-1]
            for target_command, item in translation[comamnd_key].items():
                template_command = ''
                for template in item['parent_node']:
                    template_command += ' ' + template
                template_command += ' ' + target_command
                trans_templates.append(template_command.strip())
        return trans_templates

    def insert_parent_command(self, target_commands, src_command_id, src_command, src_depth, parent_commands: [],
                              all_params,
                              target_vendor):
        for index, parent_command in enumerate(parent_commands):
            newest_parent = None
            # 遍历是否存在与command相同的命令
            for id, (pre_src_command, translation) in target_commands.items():
                for depth, translation_commands in translation.items():
                    for command_k, command_v in translation_commands.items():
                        if command_k == parent_command:
                            newest_parent = deepcopy(command_v)

            if not newest_parent:
                parent_node = self.config_matchers[target_vendor].templates[parent_commands[0]][parent_command]
                parent_para_num = parent_node['structural_features']['param_signature']['count']
                newest_parent = {'para_num': parent_para_num,
                                 'para_placeholders': [0] if parent_para_num == 0 else [0] * parent_para_num,
                                 'para_match': list(all_params),
                                 'target_command': parent_command,
                                 'parent_node': parent_commands[0:index],
                                 'source': 'rule'
                                 }
            target_commands.setdefault(src_command_id, (src_command, {}))[1].setdefault(index, {})[
                parent_command] = newest_parent

        return target_commands


class ConfigNode:
    def __init__(self, line, tag, id, source='rule'):
        self.line = line.strip()
        self.tag = tag
        self.children = []
        self.id = [id]
        self.source = source

    def add_child(self, child_node):
        self.children.append(child_node)

    def to_lines(self, indent=-1):
        if indent == -1:
            lines = [self.line]
        else:
            lines = [" " * indent + self.line]
        for child in self.children:
            lines.extend(child.to_lines(indent + 1))
        return lines

    def to_mapping_graph(self):
        lines = [(self.line, self.id, self.source)]
        for child in self.children:
            lines.extend(child.to_mapping_graph())
        return lines

    def __eq__(self, other):
        return isinstance(other, ConfigNode) and self.line == other.line

    def merge(self, other):
        for other_child in other.children:
            merged = False
            for child in self.children:
                if child == other_child:
                    child.merge(other_child)
                    child.id.extend(other_child.id)
                    merged = True
                    break
            if not merged:
                self.children.append(deepcopy(other_child))

    def get_all_tags(self):
        """遍历整棵树，收集所有节点的tag（line）"""
        tags = []

        def dfs(node):
            if node.tag:
                tags.append(node.tag)
            for child in node.children:
                dfs(child)

        dfs(self)
        return tags


# 最后阶段使用大模型做配置映射，保留接口，后续补充
class Translation_Model:
    def __init__(self, model_name: str, config_model_dir: str, vendors: [],
                 endpoint_url: str = 'https://api.deepseek.com/v1'):
        if 'gpt' in model_name:
            api_key = os.getenv("OPENAI_KEY")
        elif 'aliyun' in model_name:
            api_key = os.getenv("ALIYUN_API_KEY")
            model_name = model_name.replace('aliyun_', '')
        elif 'deepseek' in model_name:
            api_key = os.getenv("DEEPSEEK_API_KEY")
        else:
            raise ValueError("Invalid model name")
        self.model_name = model_name
        self.llm_model = OpenAI(api_key=api_key, base_url=endpoint_url)
        self.config_models = self.load_config_models(config_model_dir, vendors)

    def load_config_models(self, config_model_dir: str, vendors: []):
        config_models = {}
        for vendor in vendors:
            config_model_path = config_model_dir.format(vendor)
            with open(config_model_path, 'r') as file:
                config_model = json.load(file)
                config_models[vendor] = config_model
        return config_models

    # def param_map_rewrite(self, vendor, src_command, target_vendor, target_temp_command):
    #     prompt_file = project_root / 'resource/parameter_mapping_F_prompt.txt'
    #     prompt = open(prompt_file, 'r', encoding='utf-8').read()
    #     prompt = prompt.replace("{vendor}", vendor)
    #     prompt = prompt.replace("{target_vendor}", target_vendor)
    #     prompt = prompt.replace("{src_command}", src_command)
    #     prompt = prompt.replace("{target_command}", target_temp_command)
    #
    #     messages = [
    #         {"role": "user", "content": prompt}
    #     ]
    #     for i in range(3):
    #         try:
    #             response = self.llm_model.chat.completions.create(
    #                 model=self.model_name,
    #                 messages=messages,
    #                 response_format={
    #                     'type': 'json_object'
    #                 }
    #             )
    #             json_response = response.choices[0].message.content
    #             json_response = json.loads(json_response)
    #             return json_response.get('target_command', '')
    #         except Exception as e:
    #             print(f"第 {i + 1} 次尝试失败，错误信息: {str(e)}")
    #     return ''

    def find_command_template(self, vendor, command_template):
        # 在字典中递归寻找该命令
        def find_command(template_dict, target_command):
            for key, value in template_dict.items():
                if key == target_command:
                    return value
                if isinstance(value, dict):
                    result = find_command(value, target_command)
                    if result:
                        return result
            return None

        result = find_command(self.config_models[vendor], command_template)
        if result:
            return result
        return None

    def param_map_repair(self, target_vendor, command_v):
        prompt_file = project_root / 'resource/parameter_mapping_F_prompt2.txt'
        prompt = open(prompt_file, 'r', encoding='utf-8').read()
        command_template_info = self.find_command_template(target_vendor, command_v['target_command'])
        if not command_template_info:
            raise ValueError(f"未找到命令模板: {command_v['target_command']}")

        command_object = {
            'para_match': command_v['para_match'],
            'target_command': command_v['target_command'],
            'para_num': len(command_template_info['parameters'])
        }

        param_info = []
        for index, parameter in enumerate(command_template_info['parameters']):
            param_info.append(f"parameter{index}: " + ','.join([f"{k}:{v}" for k, v in parameter.items()]))
        param_info_str = '\n'.join(param_info)

        prompt = prompt.replace("{param_info}", str(param_info_str))
        prompt = prompt.replace("{command_template}", command_v['target_command'])
        prompt = prompt.replace("{param_num}", str(len(command_template_info['parameters'])))
        prompt = prompt.replace("{target_vendor}", target_vendor)
        prompt = prompt.replace("{param_list}", str(command_v['para_match']))
        prompt = prompt.replace("{command_example}", command_template_info['command'])
        messages = [
            {"role": "user", "content": prompt}
        ]
        for i in range(3):
            try:
                response = self.llm_model.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={
                        'type': 'json_object'
                    }
                )
                json_response = response.choices[0].message.content
                # match = re.search(r'\{.*?\}', json_response, re.DOTALL)
                # json_response = json.loads(match.group())
                json_response = json.loads(json_response)
                if isinstance(json_response, dict):
                    if 'para_match' not in json_response:
                        raise ValueError(f"未找到命令模板: {command_v['target_command']}")
                    json_response.update({
                        "target_command": command_v['target_command'],
                    })
                    return json_response
            except Exception as e:
                print(f"param mapping 第 {i + 1} 次尝试失败，错误信息: {str(e)}")
                print(json_response)
        return ''

    def get_complete_commands(self, source_command, source_total_config):
        complete_commands = []
        source_total_commands = parse_config_file_content_intact(source_total_config)
        for complete_command in source_total_commands:
            if source_command in complete_command:
                complete_commands.append(complete_command)
        return '\n'.join(complete_commands)

    def llm_command_mapping(self, source_command, source_vendor, target_vendor, source_total_config):
        prompt_file = project_root / 'resource/command_mapping_F_prompt.txt'
        prompt = open(prompt_file, 'r', encoding='utf-8').read()

        prompt = prompt.replace("{source_vendor}", source_vendor)
        if source_vendor == 'Juniper':
            source_command = self.get_complete_commands(source_command, source_total_config)

        prompt = prompt.replace("{source_command}", source_command)
        prompt = prompt.replace("{target_vendor}", target_vendor)
        prompt = prompt.replace("{source_total_config}", source_total_config)

        messages = [
            {"role": "user", "content": prompt}
        ]
        for i in range(2):
            try:
                response = self.llm_model.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    # response_format={
                    #     'type': 'json_object'
                    # }
                )
                # json_response = response.choices[0].message.content
                # json_response = json.loads(json_response)
                # target_command = json_response['target_command']
                response = response.choices[0].message.content
                matches = re.findall(r'##\s*(.*?)\s*##', response, re.DOTALL)
                target_commands = []
                for match in matches:
                    target_commands.extend(match.split('\n'))

                if len(target_commands) == 0:
                    print("llm mapping returns 0 results")
                matched_results = []
                for target_command in target_commands:
                    target_command = target_command.strip()
                    command_template = self.find_command_template(target_vendor, target_command)

                    matched_results.append({
                        "para_map": [],
                        "trans_command": target_command,
                        "parent_command": [],
                        "root": target_command,
                        "source": "llm",
                        "origin_reponse": response,  # 保存原始响应
                        "trans_template": command_template
                    })

                return matched_results
            except Exception as e:
                print(f"llm command mapping 第 {i + 1} 次尝试失败，错误信息: {str(e)}")
                print(target_command)
        return None


# json文件加载
def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data


# 规则映射库加载
def mapping_library_load(file_path, vendors, manual_mapping_path=None, error_mapping_path=None, topk=3):
    mapping_libraries = {}
    for vendor in vendors:
        for target_vendor in vendors:
            if vendor == target_vendor:
                continue
            path = file_path.format(vendor, target_vendor)
            library_name = '{}_{}'.format(vendor, target_vendor)
            mapping_libraries[library_name] = load_json_file(path)
            if error_mapping_path:
                error_mapping = load_json_file(error_mapping_path.format(vendor, target_vendor))
                for key in error_mapping:
                    if key in mapping_libraries[library_name]:
                        del mapping_libraries[library_name][key]
            if manual_mapping_path:
                manual_mapping = load_json_file(manual_mapping_path.format(vendor, target_vendor))
                if topk != 3:
                    for key, value in list(manual_mapping.items())[:-abs(topk - 3)]:
                        mapping_libraries[library_name][key] = value
                else:
                    mapping_libraries[library_name].update(manual_mapping)

    return mapping_libraries


# 配置匹配器加载
def config_matchers_load(file_path, config_model_path, module_match_path, vendors, topk=3):
    config_matchers = {}
    for vendor in vendors:
        command_templates = load_json_file(file_path.format(vendor))
        config_model = load_json_file(config_model_path.format(vendor))
        module_match = {vendor1: load_json_file(module_match_path.format(vendor1, vendor))
                        for vendor1 in vendors if vendor1 != vendor}
        config_matchers[vendor] = ConfigMatcher(vendor, command_templates, config_model, module_match, topk=topk)
    return config_matchers


def config_model_load(config_model_dir, vendors):
    config_models = {}
    for vendor in vendors:
        config_models[vendor] = load_json_file(config_model_dir.format(vendor))
        if vendor == 'Juniper':
            config_models['conbined_Juniper'] = load_json_file(config_model_dir.format('Juniper_combined'))
    return config_models


def process_juniper_json(json_config):
    processed_json = {}
    for k, v in json_config.items():
        if 'template' in v:
            del v['template']
        if isinstance(v, dict):
            for command, info in v.items():
                processed_json[command] = info
    return processed_json


if __name__ == "__main__":
    vendors = ["Cisco", "HUAWEI", "Juniper"]
    # mapping_library_path = str(project_root / 'dataset_multi_vendor_config/mapping_template_library_examined/{}_{}.json')
    mapping_library_path = f'./dataset_multi_vendor_config/mapping_template_library/scale400/{{}}_{{}}.json'

    templates_path = f'./dataset_multi_vendor_config/config_command_node/scale400/{{}}.json'
    config_model_dir = f'./dataset_multi_vendor_config/config_model/scale400/{{}}.json'
    module_match_path = './dataset_multi_vendor_config/mapping_template_library/scale400/{}_{}_module_match.json'
    # 加载规则映射库
    print('Mapping library loading.')
    mapping_libraries = mapping_library_load(mapping_library_path, vendors)
    # 加载配置匹配器
    print('Config matchers loading.')
    config_matchers = config_matchers_load(templates_path, config_model_dir, module_match_path, vendors)
    # 文本嵌入模型加载
    print('Embedding model loading.')
    local_EMmodel_path = str(project_root / 'EmbeddingModel/MiniLM-L6-v2')
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": device})

    # 加载用于配置翻译的语言模型
    # translation_llm = Translation_Model('aliyun_deepseek-v3', config_model_dir=config_model_dir, vendors=vendors,
    #                                     endpoint_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    translation_llm = {}
    # 创建翻译器
    config_translater = Config_Translater(mapping_libraries, config_matchers,
                                          translation_llm, embedding_model)

    # translation test
    file_name = 'ne_mpls-l3vpn-v4_0016_0'
    source_config_dir = f'./experiment/train_dataset/command_tree/Cisco/{file_name}.json'
    # experiment/test_dataset/command_tree/Cisco/ne_mpls-l3vpn-v4_0016_0.json
    source_vendor = 'Cisco'
    target_vendor = 'Juniper'  # 'HUAWEI'
    json_config = load_json_file(source_config_dir)
    # 翻译Cisco配置到HUAWEI配置

    trans_res, trans_mapping_info, trans_templates, map_rule_freq = config_translater.translation_without_llm(
        json_config, source_vendor, target_vendor)

    print(f'Translation result of {target_vendor} is: \n{trans_res}')

    # save_path = str(
    #     project_root / f'dataset_multi_vendor_config/translation_config/{source_vendor}_{target_vendor}/{file_name}.txt')
    # with open(save_path, 'w', encoding='utf-8') as file:
    #     file.write(translation_result)
    # save_path = str(project_root / 'dataset_multi_vendor_config/translation_config/Cisco_Juniper/{}.txt'.format(file_name))
    # translation_result = config_translater.translation(json_config, 'Cisco', 'Juniper')
    # with open(save_path, 'w', encoding='utf-8') as file:
    #     file.write(translation_result)
    # print(f'Translation result of Juniper is:\n{translation_result}')
