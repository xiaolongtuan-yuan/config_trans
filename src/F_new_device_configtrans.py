# 从json解析配置到目标供应商配置
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


warnings.filterwarnings("ignore", category=UserWarning, module="torch")

# 指定设备
device = "cuda:0"  # 使用GPU 1
project_root = Path(__file__).parent.parent


# 同阶段4--CommandNode
class CommandNode:
    def __init__(self, structural_features, semantic_features, embedding_model):
        # 结构特征
        self.structural_features = {}

        # 语义特征
        self.semantic_features = {}

        # 参数语义特征
        self.paras_semantic_features = []

        # 上下文拓扑特征
        self._parse_context_topology(structural_features['parent_command'])

        # 参数签名特征
        self._build_param_signature(structural_features['params'])

        # 深度特征
        self._calculate_depth_levels(structural_features['depth'])

        # 语义特征
        self._generate_semantic_embedding(structural_features, semantic_features, embedding_model)

        # 参数语义特征
        self._generate_para_semantic_embedding(semantic_features, embedding_model)

    def _parse_context_topology(self, parent_command):
        """解析上下文拓扑关系"""
        self.structural_features['context_topology'] = {
            'parent_command': parent_command,  # 父节点命令
        }

    def _build_param_signature(self, params):
        """构建参数特征签名"""
        param_spec = {
            'count': len(params),
            'order': [p['type'] for p in params]
            # 'constraints': []
        }
        '''
        for p in params:
            constraint = {}
            if p.get('format'):
                constraint['format'] = p['format']
            if p.get('options'):
                constraint['predefined'] = p['options']
            param_spec['constraints'].append(constraint)
        '''
        self.structural_features['param_signature'] = param_spec

    def _calculate_depth_levels(self, depth):
        """# 计算物理/逻辑层级深度
        physical_depth = template.count('/')  # 使用/表示层级
        logical_depth = self._infer_logical_depth(template)"""
        self.structural_features['command_depth'] = depth

    def _generate_semantic_embedding(self, structural_features, semantic_features, embedding_model):
        """生成语义嵌入向量"""
        # 使用预训练模型获取基础语义(配置模板，命令，解释)
        '''结构特征T_{s} ，包括了配置命令层级，参数数量，父视图配置命令
           功能特征T_{f}，包括配置命令的模板，命令示例以及解释
           参数合集特征T_{P}，汇总了所有配置参数的名称、类型与解释'''
        structural_text = str(structural_features['depth']) + \
                          str(len(structural_features['params'])) + \
                          structural_features['parent_command']

        function_text = semantic_features['template'] + \
                       semantic_features['command'] +\
                       semantic_features['explanation']

        '''base_embedding = self._get_base_embedding(embedding_model,
                                                  semantic_features['template']
                                                  + semantic_features['command']
                                                  + semantic_features['explanation'])'''

        structural_embedding = self._get_base_embedding(embedding_model, structural_text)
        function_embedding = self._get_base_embedding(embedding_model, function_text)

        # 参数增强语义(所有参数的名字与解释)
        param_text = ' '.join([p['name'] + p['explanation'] for p in semantic_features['parameters']])
        param_embedding = self._get_param_embedding(embedding_model, param_text)

        # 融合特征
        self.semantic_features = self._fuse_embeddings(
            structural_embedding, function_embedding, param_embedding
        )

    def _generate_para_semantic_embedding(self, semantic_features, embedding_model):
        # 参数语义(单个参数的名字+完整配置命令解释)
        for p in semantic_features['parameters']:
            para_text = p['name'] + p['explanation'] + semantic_features['template']
            self.paras_semantic_features.append(self._get_param_embedding(embedding_model, para_text).tolist())

    # 语义嵌入向量   
    def _get_base_embedding(self, embedding_model, text):
        return torch.tensor(embedding_model.embed_query(text))

    def _get_param_embedding(self, embedding_model, text):
        return torch.tensor(embedding_model.embed_query(text))

    def _fuse_embeddings(self, structure, function, param):
        # 使用注意力机制融合特征
        attention_weights = torch.softmax(torch.cat([structure, function, param]), dim=0)
        return (structure * attention_weights[0] + function * attention_weights[1] + param * attention_weights[2]).tolist()

# 同阶段5--ConfigMatcher
class ConfigMatcher:
    def __init__(self, target_command_templates, semantic_topk=3):
        self.templates = target_command_templates  # 预加载的配置(节点)模板库
        self.semantic_topk = semantic_topk  # 语义匹配top k纳入候选集

    def find_best_match(self, command_node):
        """执行多级匹配流程"""
        # 第一阶段：基础语义匹配--功能匹配（计算对比所有配置节点语义嵌入排序）
        ranked_candidates = self._semantic_ranking(command_node)
        match_score = sum([sim[1] for sim in ranked_candidates]) / len(ranked_candidates)

        # 第二阶段：参数语义匹配--组织/结构特征（计算对比候选集中所有参数嵌入）
        para_match = self._param_semantic_match(command_node, ranked_candidates)

        # 第三阶段：整合匹配的参数对，并延伸至命令
        match_result = self._integrate_commands(ranked_candidates, para_match)

        return match_result, match_score

    def _semantic_ranking(self, command_node):
        """语义特征排序"""
        semantic_embedding = torch.tensor(command_node.semantic_features, dtype=torch.float32).unsqueeze(0).cuda()
        target_embeddings = []

        for template, target_node in self.templates.items():
            if not 'semantic_features' in target_node:
                continue
            target_embedding = torch.tensor(target_node['semantic_features'], dtype=torch.float32).unsqueeze(0)
            target_embeddings.append(target_embedding)

        target_embeddings = torch.cat(target_embeddings, dim=0).cuda()

        # 计算余弦相似度
        norm_semantic = torch.norm(semantic_embedding, dim=1, keepdim=True)
        norm_target = torch.norm(target_embeddings, dim=1, keepdim=True)
        dot_product = torch.matmul(semantic_embedding, target_embeddings.T)
        similarities = dot_product / (norm_semantic * norm_target.T)

        similarities = similarities.squeeze(0).cpu().numpy()
        template_list = list(self.templates.keys())
        similarity_pairs = [(template, sim) for template, sim in zip(template_list, similarities)]

        return sorted(similarity_pairs, key=lambda x: x[1], reverse=True)[:self.semantic_topk]

    def _get_parent_commands(self, ranked_candidates):
        # 按照配置视图层次，加入所有的父配置命令
        ranked_candidates = [candidate_command[0] for candidate_command in ranked_candidates]  # 候选配置命令模板集合

        # 获取所有的父配置命令，不需要递归了
        def _parent_commands(candidate: list) -> list:
            for command in candidate:
                parent_commands = self.templates[command]['structural_features']['context_topology']['parent_command']
                for parent_command in parent_commands:
                    if parent_command not in candidate:
                        candidate.append(parent_command)
            return candidate

        candidate = _parent_commands(ranked_candidates)  # 补全父配置命令之后候选集
        return candidate

    def _param_semantic_match(self, command_node, ranked_candidates):
        """参数语义匹配"""
        candidate = self._get_parent_commands(ranked_candidates)
        para_match = []
        # 为command中每个参数语义需求一个最佳参数匹配
        for para_embedding in command_node.paras_semantic_features:
            para_embedding = np.array(para_embedding).reshape(1, -1)
            all_similarities = []
            # 对比每一个命令中的参数语义
            for candidate_command in candidate:
                try:
                    candidate_paras = self.templates[candidate_command]['parameter_features']  # list
                except KeyError:
                    continue
                similarities = []
                for index, candidate_para_embedding in enumerate(candidate_paras):
                    candidate_para_embedding = np.array(candidate_para_embedding).reshape(1, -1)
                    sim = cosine_similarity(para_embedding, candidate_para_embedding)
                    similarities.append((candidate_command, sim, index))  # 配置模板，相似度，参数编号
                # 保存每个配置命令中与当前待匹配参数最匹配的参数
                # print(len(similarities))
                if len(similarities) > 0:
                    all_similarities.append(sorted(similarities, key=lambda x: x[1], reverse=True)[0])
            if len(all_similarities) > 0:
                para_match.append(sorted(all_similarities, key=lambda x: x[1], reverse=True)[0])
        return para_match

    def _integrate_commands(self, ranked_candidates, para_match):
        # 带参数的配置命令映射
        if para_match:
            # print('command with parameters:')
            match_list = []
            for index, match_item in enumerate(para_match):
                # print('[parameter{}]'.format(index+1), 'correspond [parameter{}] of command -- {}'.format(match_item[2]+1, match_item[0]))
                match_list.append([index, match_item[2], match_item[0], self.templates[match_item[0]]['structural_features']['context_topology']['parent_command']])
            return match_list
        # 不带参数命令映射
        else:
            # print('command without parameters:')
            # print('corespond command {}'.format(ranked_candidates[0][0]))
            return [ranked_candidates[0][0], self.templates[ranked_candidates[0][0]]['structural_features']['context_topology']['parent_command']]

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
def parse_command_node(Command_nodes: dict, config_model: dict, parent_command='system', depth=0):
    for k, sub_dict in config_model.items():
        # print(k, sub_dict)
        if not isinstance(sub_dict, dict):
            continue

        template_key = sub_dict.get("template")
        if not template_key:
            # 没有 template 就跳过
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
            # 创建命令节点
            # command_node = CommandNode(structural_feature, semantic_feature, embedding_model)
            Command_nodes[k] = {'structural_feature': structural_feature, 'semantic_feature': semantic_feature}
            # print(k)

        '''for child_k, child_v in sub_dict.items():
            print(child_k, child_v)
            if not isinstance(child_v, dict):
                continue'''
        Command_nodes = parse_command_node(Command_nodes, sub_dict, k, depth + 1)
    return Command_nodes


# 设备配置翻译器
class Config_Translater:

    def __init__(self, mapping_libraries, config_matchers, translation_llm,
                 embedding_model):
        self.mapping_libraries = mapping_libraries  # 加载配置模板映射规则库
        self.config_matchers = config_matchers  # 加载配置命令匹配器
        self.translation_llm = translation_llm  # 加载配置翻译模型
        self.embedding_model = embedding_model  # 加载嵌入模型
        # 初始化配置命令匹配器
        # self.config_matchers = self.initialize_config_matchers(target_command_templates)                

    '''
    def initialize_config_matchers(self, target_command_templates):
        self.config_matchers = {}
        for vendor, target_command_template in target_command_templates.items():
            self.config_matchers[vendor] = ConfigMatcher(target_command_template)
    '''

    # 进行配置翻译
    def translation(self, json_configuration, vendor, target_vendor):
        config_match = {}  # 保存翻译（匹配）集合
        # 给juniper配置模型加个保险
        if vendor == 'Juniper':
            json_configuration = insert_template(json_configuration)
        commands_feature = {}  # 分拆每一条配置命令特征
        commands_feature = parse_command_node(commands_feature, json_configuration)

        # 阶段一：规则映射rule_mapping, rest_commands_feature是在映射库中不存在的配置命令
        rest_commands_feature, config_match = self.rule_mapping(commands_feature,
                                                                config_match, vendor, target_vendor)

        # 阶段二：模糊映射fuzzy_mapping-->针对规则映射库未覆盖的配置命令
        config_match = self.fuzzy_mapping(rest_commands_feature, config_match, vendor, target_vendor)

        # 阶段四：配置命令编排，配置参数直接填充
        arranged_config = self.config_arranging(config_match, target_vendor)
        # print(json.dumps(arranged_config, indent=4, ensure_ascii=False))

        # 阶段五：llm配置参数映射与修正
        # target_config = self.parameter_mapping_with_LLM_rewrite(arranged_config, vendor, target_vendor)
        target_config = self.parameter_mapping_with_LLM_remapping(arranged_config, vendor, target_vendor)

        # print(json.dumps(target_config, indent=4, ensure_ascii=False))

        # 阶段六：输出并保存翻译的配置命令
        trans_res, trans_mapping_info = self.print_and_save_translation_config(target_config, target_vendor)

        return trans_res, trans_mapping_info

    def translation_with_tau(self, json_configuration, vendor, target_vendor, tau=0.65):
        '''
        测试tau阈值对翻译效果的影响
        '''
        config_match = {}  # 保存翻译（匹配）集合
        # 给juniper配置模型加个保险
        if vendor == 'Juniper':
            json_configuration = insert_template(json_configuration)
        commands_feature = {}  # 分拆每一条配置命令特征
        commands_feature = parse_command_node(commands_feature, json_configuration)

        # 阶段一：规则映射rule_mapping, rest_commands_feature是在映射库中不存在的配置命令
        rest_commands_feature, config_match = self.rule_mapping(commands_feature,
                                                                config_match, vendor, target_vendor)

        # 阶段二：模糊映射fuzzy_mapping-->针对规则映射库未覆盖的配置命令
        config_match = self.fuzzy_mapping(rest_commands_feature, config_match, vendor, target_vendor, tau=tau)

        # 阶段四：配置命令编排，配置参数直接填充
        arranged_config = self.config_arranging(config_match, target_vendor)
        # print(json.dumps(arranged_config, indent=4, ensure_ascii=False))

        # 阶段五：llm配置参数映射与修正
        # target_config = self.parameter_mapping_with_LLM_rewrite(arranged_config, vendor, target_vendor)
        target_config = self.parameter_mapping_with_LLM_remapping(arranged_config, vendor, target_vendor)

        # print(json.dumps(target_config, indent=4, ensure_ascii=False))

        # 阶段六：输出并保存翻译的配置命令
        trans_res, trans_mapping_info = self.print_and_save_translation_config(target_config, target_vendor)

        return trans_res, trans_mapping_info

    def translation_without_llm(self, json_configuration, vendor, target_vendor, istatistics=False):
        '''
        启发式翻译
        '''
        config_match = {}  # 保存翻译（匹配）集合
        # 给juniper配置模型加个保险
        if vendor == 'Juniper':
            json_configuration = insert_template(json_configuration)
        commands_feature = {}  # 分拆每一条配置命令特征
        commands_feature = parse_command_node(commands_feature, json_configuration)

        # 阶段一：规则映射rule_mapping, rest_commands_feature是在映射库中不存在的配置命令
        rest_commands_feature, config_match = self.rule_mapping(commands_feature,
                                                                config_match, vendor, target_vendor)

        if not istatistics:
            # 阶段二：模糊映射fuzzy_mapping-->针对规则映射库未覆盖的配置命令
            config_match = self.fuzzy_mapping(rest_commands_feature, config_match, vendor, target_vendor,  tau=0)

            # 阶段四：配置命令编排，配置参数直接填充
            arranged_config = self.config_arranging(config_match, target_vendor)
            # print(json.dumps(arranged_config, indent=4, ensure_ascii=False))

            # 阶段五：参数映射
            target_config = self.parameter_mapping(arranged_config, vendor, target_vendor)

            # 阶段六：输出并保存翻译的配置命令
            trans_res, trans_mapping_info = self.print_and_save_translation_config(target_config, target_vendor)

            return trans_res, trans_mapping_info
        else:
            statistic_data = {
                "command_count": len(commands_feature),
                "rule_ccount": len(config_match),
                "llm_ccount": 0
            }
            map_rule_freq = {}
            for command, match in config_match.items():
                map_rule = str([match['template'], match['match']])

                if map_rule not in map_rule_freq.keys():
                    map_rule_freq[map_rule] = 1
                else:
                    map_rule_freq[map_rule] += 1
            _, filtered_commands_feature = self.fuzzy_mapping_for_statistic(rest_commands_feature, config_match, vendor, target_vendor)
            statistic_data['llm_ccount'] = len(filtered_commands_feature)
            return statistic_data, map_rule_freq


    # 阶段一借助模板映射库实现规则映射
    def rule_mapping(self, commands_feature, config_match, vendor, target_vendor):
        rest_commands_feature = {}  # 保存不包含在规则映射库中的配置命令
        specific_mapping_library = self.mapping_libraries['{}_{}'.format(vendor, target_vendor)]
        # 查找每一条配置在规则库里的映射关系
        for command, feature in commands_feature.items():
            # 不在配置映射库中
            template = feature['semantic_feature']['template']
            if template not in specific_mapping_library.keys():
                rest_commands_feature[command] = feature
                continue
            # 在映射库中的配置命令
            config_match[command] = {'template': template, 'match': specific_mapping_library[template]}

        return rest_commands_feature, config_match

    # 阶段二借助目标供应商配置模板基于语义相似度实现模糊映射
    def fuzzy_mapping(self, rest_commands_feature, config_match, vendor, target_vendor, tau=0.65):
        # 根据语义做模糊匹配
        filtered_commands_feature = []
        for command, feature in rest_commands_feature.items():
            structural_feature = feature['structural_feature']
            semantic_feature = feature['semantic_feature']
            # 创建命令节点，执行语义/参数嵌入
            command_node = CommandNode(structural_feature, semantic_feature, self.embedding_model)
            matched_result, match_score = self.config_matchers[target_vendor].find_best_match(command_node)
            if match_score > tau:  # 匹配度大于阈值
                template = feature['semantic_feature']['template']
                config_match[command] = {'template': template, 'match': matched_result}
                # 补充现有的模板库
                self.mapping_libraries['{}_{}'.format(vendor, target_vendor)][template] = matched_result
            else:
                filtered_commands_feature.append(command)
                matched_result = self.translation_llm.llm_command_mapping(command, vendor,
                                                                          target_vendor)  # matched_result = str
                result_node = {"structural_features": {'command_depth': structural_feature['depth'],
                                                      'param_signature': {},
                                                      'context_topology': {'parent_command': []}}}

                self.config_matchers[target_vendor].templates[matched_result] = result_node
                template = feature['semantic_feature']['template']
                config_match[command] = {'template': template, 'match': matched_result}

        return config_match

    def fuzzy_mapping_for_statistic(self, rest_commands_feature, config_match, vendor, target_vendor, tau=0.65):
        # 根据语义做模糊匹配
        filtered_commands_feature = []
        for command, feature in rest_commands_feature.items():
            structural_feature = feature['structural_feature']
            semantic_feature = feature['semantic_feature']
            # 创建命令节点，执行语义/参数嵌入
            command_node = CommandNode(structural_feature, semantic_feature, self.embedding_model)
            matched_result, match_score = self.config_matchers[target_vendor].find_best_match(command_node)
            if match_score > tau:  # 匹配度大于阈值
                template = feature['semantic_feature']['template']
                config_match[command] = {'template': template, 'match': matched_result}
                # 补充现有的模板库
                self.mapping_libraries['{}_{}'.format(vendor, target_vendor)][template] = matched_result
            else:
                filtered_commands_feature.append(command)
                matched_result = command
                result_node = {"structural_features": {'depth': structural_feature['depth'],
                                                      'params': [],
                                                      'parent_command': 'system'}}

                self.config_matchers[target_vendor].templates[matched_result] = result_node
                template = feature['semantic_feature']['template']
                config_match[command] = {'template': template, 'match': matched_result}

        return config_match, filtered_commands_feature

    # 阶段三使用大模型做配置映射，保留接口，当前翻译流程关注前两阶段效果
    def LLMmodel_mapping(self, rest_commands_feature, config_match, vendor, target_vendor):
        raise NotImplementedError

    # 阶段四进行配置编排，对应正确的视图
    def config_arranging(self, config_matches, target_vendor):
        arranged_command = {}
        # Juniper没有视图层级, 按顺序输出配置命令即可
        for item_k, item_v in config_matches.items():
            # 依据翻译命令的视图深度实现编排{0:{c0:[4,[0,0,1,1]]}}
            # paras-->具体配置参数值, depth-->第零层, translated_command-->命令模板, 
            # para_num-->参数数量, para_placeholders-->[0,0,1,1]参数填充占位标识,
            # para_match --> 参数映射,  target_command--> 最终翻译命令
            paras = self.para_extract(item_k, config_matches[item_k]['template'])
            arranged_command[item_k] = {'para': paras}
            # 如果是list需要遍历整合信息
            if isinstance(item_v['match'][0], list):
                for para_match in item_v['match']:  # 遍历每一个参数映射信息
                    # 查找翻译命令的视图层级
                    if len(para_match) == 4:
                        translated_command = para_match[2]  # 翻译的配置命令
                    elif len(para_match) == 2:
                        translated_command = para_match[0]
                    else:
                        raise ValueError("para_match length error")
                    # 配置命令节点
                    try:
                        command_node = self.config_matchers[target_vendor].templates[translated_command]  # 至少这这前面的不能随便改
                    except KeyError:
                        print(f"KeyError: {translated_command}")
                        continue
                    # 命令视图层级
                    depth = command_node['structural_features']['command_depth']
                    # 参数数量
                    para_num = command_node['structural_features']['param_signature']['count']
                    parent_commands = para_match[-1]
                    # 如果不包含该层级
                    if depth not in arranged_command[item_k].keys():
                        para_placeholders = [0] if para_num == 0 else [
                                                                          0] * para_num  # 为什么每一个参数映射信息都要有一个站位符呢？而且站位符的长度是目标命令的参数数量？
                        if len(para_match) == 4:
                            if not -1 in para_match:
                                try:
                                    para_placeholders[para_match[1]] = 1  # ==1表示目标命令的该位置被映射到了
                                except IndexError:
                                    print(f"IndexError: para_placeholders index out of range: {para_match}")
                        arranged_command[item_k][depth] = {translated_command:
                                                               {'para_num': para_num,
                                                                'para_placeholders': para_placeholders,
                                                                'para_match': self.match_and_extract(paras, para_num,
                                                                                                     item_v['match'],
                                                                                                     translated_command),
                                                                'target_command': translated_command,
                                                                'parent_node': parent_commands}
                                                           }
                    # 如果该层级中不包含这一配置命令
                    elif translated_command not in arranged_command[item_k][depth].keys():
                        # 参数填充占位符
                        para_placeholders = [0] if para_num == 0 else [
                                                                          0] * para_num
                        if len(para_match) == 4:
                            if not -1 in para_match:
                                try:
                                    para_placeholders[para_match[1]] = 1
                                except IndexError:
                                    print(f"IndexError: para_placeholders index out of range: {para_match}")
                        arranged_command[item_k][depth].update({translated_command:
                                                                    {'para_num': para_num,
                                                                     'para_placeholders': para_placeholders,
                                                                     'para_match': self.match_and_extract(paras,
                                                                                                          para_num,
                                                                                                          item_v[
                                                                                                              'match'],
                                                                                                          translated_command),
                                                                     'target_command': translated_command,
                                                                     'parent_node': parent_commands}
                                                                })
                    # 如果该层级包含这一配置命令
                    else:
                        if len(para_match) == 4:
                            if not -1 in para_match:
                                try:
                                    arranged_command[item_k][depth][translated_command]['para_placeholders'][
                                        para_match[1]] = 1
                                except IndexError:
                                    print(f"IndexError: para_placeholders index out of range: {para_match}")
            # 都是list，没参数的只有两项，命令和父命令
            else:
                # 查找翻译命令的视图层级
                translated_command = item_v['match'][0]  # 纠正错误
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
                                                   }
        return arranged_command

    def parameter_mapping_with_LLM_remapping(self, arranged_config: dict, vendor, target_vendor) -> dict:
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

        # 参数插入配置命令模板
        # 创建一个线程池，将llm映射的任务提交给线程池
        with ThreadPoolExecutor() as executor:
            futures = []
            for src_command, translation in target_commands.items():
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
                    if len(parent_commands) > 0: # 不是根节点
                        self.insert_parent_command(target_commands, src_command, int(depth), parent_commands,
                                                   all_params, target_vendor)  # 补充父节点
                    target_commands = self.command_param_merge(target_commands, src_command,
                                                               int(depth), command, command_v)

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
    def command_param_merge(self, target_commands: dict, src_command: str, src_depth: int,
                            command: str, command_info: dict) -> dict:
        # merge标识符
        merged_flag = 0
        # 遍历是否存在与command相同的命令
        for pre_src_command, translation in target_commands.items():  # 变量名重复，已改
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
                            merged_paras = [x if x != 'none' else y for x, y in
                                            zip(command_info['para_match'], command_v['para_match'])]
                            command_v['para_placeholders'] = merged_placeholders.tolist()
                            command_v['para_match'] = merged_paras
                            merged_flag = 1
        if merged_flag == 0:
            target_commands.setdefault(src_command, {}).setdefault(src_depth, {})[command] = command_info
        return target_commands

    """
    匹配并提取符合条件的项的前两个值
    :para_match: 输入的数据结构
    :return: 符合条件的项的 [a, b] 列表
    """

    def match_and_extract(self, paras: list, para_num: int,
                          para_match: list, target_template: str) -> list:
        result = ['none'] * para_num
        if isinstance(para_match[0], list) and para_num > 0:
            for item in para_match:
                if isinstance(item, str):
                    continue
                # 检查最后一项是否匹配目标模板
                if item[2] == target_template and (not -1 in item):
                    # paras的第item[0]个参数是result的item[1]个参数
                    try:
                        result[item[1]] = paras[item[0]]
                    except Exception as e:
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
        if bool(re.search(r"\[parameter\d*\]", src_template)):
            src_regex = re.sub(r"\[parameter\d*\]", r"(\\S+)", src_template)
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
        for index, param in enumerate(params):
            # dest_template = dest_template.replace(f"[parameter{index + 1}]", '{' + param + '}')
            dest_template = dest_template.replace(f"[parameter{index + 1}]", param)
        return dest_template

    def merge_config_nodes(self, root, target_vendor):
        merged_root = ConfigNode("system")
        node_map = {}

        for child in root.children:
            key = child.line
            if key not in node_map:
                node_map[key] = deepcopy(child)
                merged_root.add_child(node_map[key])
            else:
                node_map[key].merge(child)

        return merged_root

    # 输出对应视图的配置命令
    def print_and_save_translation_config(self, target_config, target_vendor):
        trans_pairs = []
        root = ConfigNode("system")
        stack = [(root, -1)]

        # 遍历每一个需要翻译的配置命令
        for command, translation in target_config.items():
            # 遍历该需要翻译配置命令中每一层级的配置命令
            for depth, target_command in translation.items():
                if depth == -1:
                    continue
                # 输出该层级下所有的配置命令
                for target_temp, command_info in target_command.items():
                    line = command_info['target_command']
                    node = ConfigNode(line)
                    while stack and stack[-1][1] >= depth:
                        stack.pop()

                    stack[-1][0].add_child(node)
                    stack.append((node, depth))

                    trans_pairs.append(f"{command} -- {command_info['target_command']}")

        merged_config_tree = self.merge_config_nodes(root, target_vendor)

        if target_vendor == 'Juniper':
            trans_res = self.juniper_combine(merged_config_tree)
        else:
            trans_res = "\n".join(merged_config_tree.to_lines()[1:])
        trans_mapping_info = '\n'.join(trans_pairs)
        return trans_res, trans_mapping_info

    def juniper_combine(self, root):
        # 去除根节点，将树拆分为n个子树，深度遍历每个子树至根节点，将其line值用' '拼接为一条命令
        if root.line == "system":
            subtrees = root.children
        else:
            subtrees = [root]
        commands = []
        def dfs(node, current_command):
            current_command.append(node.line)
            for child in node.children:
                dfs(child, current_command)

        for subtree in subtrees:
            current_command = []
            dfs(subtree, current_command)
            # 用空格拼接为一条命令
            commands.append(" ".join(current_command))

        trans_res = '\n'.join(commands)
        return trans_res


    def insert_parent_command(self, target_commands, src_command, src_depth, parent_commands:[], all_params, target_vendor):
        for index, parent_command in enumerate(parent_commands):
            newest_parent = None
            # 遍历是否存在与command相同的命令
            for pre_src_command, translation in target_commands.items():
                for depth, translation_commands in translation.items():
                    for command_k, command_v in translation_commands.items():
                        if command_k == parent_command:
                            newest_parent = deepcopy(command_v)

            if not newest_parent:
                parent_node = self.config_matchers[target_vendor].templates[parent_command]
                parent_para_num = parent_node['structural_features']['param_signature']['count']
                newest_parent = {'para_num': parent_para_num,
                                 'para_placeholders': [0] if parent_para_num == 0 else [0] * parent_para_num,
                                 'para_match': list(all_params),
                                 'target_command': parent_command,
                                 'parent_node': parent_commands[0:index]}
            target_commands.setdefault(src_command, {}).setdefault(index, {})[parent_command] = newest_parent

        return target_commands


class ConfigNode:
    def __init__(self, line):
        self.line = line.strip()
        self.children = []

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

    def __eq__(self, other):
        return isinstance(other, ConfigNode) and self.line == other.line

    def merge(self, other):
        for other_child in other.children:
            for child in self.children:
                if child == other_child:
                    child.merge(other_child)
                    break
            else:
                self.children.append(deepcopy(other_child))


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
        prompt = prompt.replace("{target_vendor}", target_vendor)
        prompt = prompt.replace("{command_object}", str(command_object))
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
                json_response = json.loads(json_response)
                if isinstance(json_response, dict):
                    if 'para_match' not in json_response and 'target_command' not in json_response:
                        raise ValueError(f"未找到命令模板: {command_v['target_command']}")
                    return json_response
            except Exception as e:
                print(f"第 {i + 1} 次尝试失败，错误信息: {str(e)}")
        return ''

    def llm_command_mapping(self, source_command, source_vendor, target_vendor):
        prompt_file = project_root / 'resource/command_mapping_F_prompt.txt'
        prompt = open(prompt_file, 'r', encoding='utf-8').read()

        prompt = prompt.replace("{source_vendor}", source_vendor)
        prompt = prompt.replace("{source_command}", source_command)
        prompt = prompt.replace("{target_vendor}", target_vendor)

        messages = [
            {"role": "user", "content": prompt}
        ]
        for i in range(2):
            try:
                response = self.llm_model.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={
                        'type': 'json_object'
                    }
                )
                json_response = response.choices[0].message.content
                json_response = json.loads(json_response)
                return json_response['target_command']
            except Exception as e:
                print(f"第 {i + 1} 次尝试失败，错误信息: {str(e)}")
        return ''


# json文件加载
def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        content = json_file.read()
        # pattern = r'\[parameter\d\]'
        # content = re.sub(pattern, '[parameter]', content)
        data = json.loads(content)
    return data


# 规则映射库加载
def mapping_library_load(file_path, vendors):
    mapping_libraries = {}
    for vendor in vendors:
        for target_vendor in vendors:
            if vendor == target_vendor:
                continue
            path = file_path.format(vendor, target_vendor)
            library_name = '{}_{}'.format(vendor, target_vendor)
            mapping_libraries[library_name] = load_json_file(path)
    return mapping_libraries


# 配置匹配器加载
def config_matchers_load(file_path, vendors, semantic_topk=3):
    config_matchers = {}
    for vendor in vendors:
        command_templates = load_json_file(file_path.format(vendor))
        config_matchers[vendor] = ConfigMatcher(command_templates, semantic_topk=semantic_topk)
    return config_matchers


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
    mapping_library_path = str(
        project_root / 'dataset_multi_vendor_config/mapping_template_library/scale388en/{}_{}_388.json')

    templates_path = str(project_root / 'dataset_multi_vendor_config/config_command_node/scale388en/{}_388.json')
    config_model_dir = str(project_root / 'dataset_multi_vendor_config/config_model/scale388en/{}_388.json')

    # 加载规则映射库
    print('Mapping library loading.')
    mapping_libraries = mapping_library_load(mapping_library_path, vendors)
    # 加载配置匹配器
    print('Config matchers loading.')
    config_matchers = config_matchers_load(templates_path, vendors)
    # 文本嵌入模型加载
    print('Embedding model loading.')
    local_EMmodel_path = str(project_root / 'EmbeddingModel/MiniLM-L6-v2')
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path,
                                            model_kwargs={"device": device})

    # 加载用于配置翻译的语言模型
    translation_llm = Translation_Model('aliyun_deepseek-v3', config_model_dir=config_model_dir, vendors=vendors,
                                        endpoint_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    # 创建翻译器
    config_translater = Config_Translater(mapping_libraries, config_matchers,
                                          translation_llm, embedding_model)

    # translation test
    file_name = 'ne_mpls-l3vpn-v4_0016_0'
    config_path = str(project_root / f'dataset_multi_vendor_config/test/{file_name}.json')

    source_vendor = 'Cisco'
    target_vendor = 'Juniper'
    json_config = load_json_file(config_path)
    if source_vendor == 'Juniper':
        json_config = process_juniper_json(json_config)
    # 翻译Cisco配置到HUAWEI配置

    translation_result, _ = config_translater.translation_without_llm(json_config, source_vendor, target_vendor)
    print(f'Translation result of {target_vendor} is: \n{translation_result}')

    # save_path = str(
    #     project_root / f'dataset_multi_vendor_config/translation_config/{source_vendor}_{target_vendor}/{file_name}.txt')
    # with open(save_path, 'w', encoding='utf-8') as file:
    #     file.write(translation_result)
    # save_path = str(project_root / 'dataset_multi_vendor_config/translation_config/Cisco_Juniper/{}.txt'.format(file_name))
    # translation_result = config_translater.translation(json_config, 'Cisco', 'Juniper')
    # with open(save_path, 'w', encoding='utf-8') as file:
    #     file.write(translation_result)
    # print(f'Translation result of Juniper is:\n{translation_result}')
