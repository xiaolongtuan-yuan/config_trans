import os
from pathlib import Path

import torch
from sklearn.metrics.pairwise import cosine_similarity
import json
import numpy as np
from tqdm import tqdm
import copy

'''
配置匹配器运行逻辑：
0、匹配到模块，获取模块相似度（根父节点语义特征对比：模版、命令、解释）
输入-->

1、对比基础语义嵌入, 获取功能相似度(基础语义特征：模板、命令、解释+所有参数名与解释)
例如：
输入-->C1([p1], [p2], [p3])（原配置命令）
输出-->C2([p1], [p2]), C3([p3]) （目标配置命令候选集）

2、对比参数语义嵌入, 获取性能/结构相似度（参数语义特征：参数名/类型/解释+配置命令解释）
输入-->C1([p1], [p2], [p3]), {C2([p1], [p2]), C3([p3])}（原配置命令+目标配置命令候选集）
输出-->{C1<->p1->p1<->C2, C1<->p2->p2<->C2, C1<->p3->p3<->C3}（配置参数对）

'''


class ConfigMatcher:
    def __init__(self, vendor, target_command_templates, config_model, module_match, topk=3):
        self.templates = target_command_templates
        self.semantic_topk = topk
        self.config_model = config_model
        self.module_match = module_match
        self.vendor = vendor
        # self.command2root = build_command2root(self.config_model)

    def find_best_match(self, source_vendor, command_node, src_root, src_root_semantic):
        # print('command_node:', command_node)
        best_root = self._module_ranking(source_vendor, src_root, src_root_semantic)
        # print('best_root:', best_root)
        # subtree_cmds = self.get_subtree_commands(best_root)
        # subtree_cmds = self.templates[best_root]
        # print('subtree_cmds:', subtree_cmds)
        # subtree_templates = {k: v for k, v in self.templates[best_root].items()}
        # 3. 基础语义匹配
        ranked_candidates = self._semantic_ranking(command_node, self.templates[best_root])
        # 4. 参数语义匹配
        para_match = self._param_semantic_match(command_node, ranked_candidates, self.templates[best_root])
        # 5. 整合
        match_result = self._integrate_commands(best_root, ranked_candidates, para_match)
        return match_result, best_root

    def _module_ranking(self, source_vendor, src_root, src_root_semantic):
        # 直接在module_match中查找
        if src_root in self.module_match[source_vendor].keys():
            return self.module_match[source_vendor][src_root]
        # 只用src_root_semantic与目标库所有根节点做匹配
        tgt_root_names = [k for k in self.templates.keys()]  # 目标库根节点
        # print('tgt_root_names:', tgt_root_names)
        tgt_root_embeddings = [torch.tensor(self.templates[k][k]['semantic_features'], dtype=torch.float32).unsqueeze(0) for k in tgt_root_names]
        tgt_root_embeddings = torch.cat(tgt_root_embeddings, dim=0).cuda()
        norm_src = torch.norm(src_root_semantic, dim=1, keepdim=True)
        norm_tgt = torch.norm(tgt_root_embeddings, dim=1, keepdim=True)
        dot_product = torch.matmul(src_root_semantic, tgt_root_embeddings.T)
        similarities = dot_product / (norm_src * norm_tgt.T)
        similarities = similarities.squeeze(0).cpu().numpy()
        best_idx = np.argmax(similarities)
        best_root = tgt_root_names[best_idx]
        return best_root

    def _semantic_ranking(self, command_node, templates=None):
        if templates is None:
            templates = self.templates
        semantic_embedding = torch.tensor(command_node['semantic_features'], dtype=torch.float32).unsqueeze(0).cuda()
        target_embeddings = []
        template_list = list(templates.keys())
        for template in template_list:
            target_embedding = torch.tensor(templates[template]['semantic_features'], dtype=torch.float32).unsqueeze(0)
            target_embeddings.append(target_embedding)
        target_embeddings = torch.cat(target_embeddings, dim=0).cuda()
        norm_semantic = torch.norm(semantic_embedding, dim=1, keepdim=True)
        norm_target = torch.norm(target_embeddings, dim=1, keepdim=True)
        dot_product = torch.matmul(semantic_embedding, target_embeddings.T)
        similarities = dot_product / (norm_semantic * norm_target.T)
        similarities = similarities.squeeze(0).cpu().numpy()
        similarity_pairs = [(template, sim) for template, sim in zip(template_list, similarities)]
        return sorted(similarity_pairs, key=lambda x: x[1], reverse=True)[:self.semantic_topk]

    def _get_parent_commands(self, ranked_candidates, templates):
        # templates[command]['structural_features']['context_topology']['parent_command']
        # 只在templates（即当前模块子树）内补全父命令
        candidate = [candidate_command[0] for candidate_command in ranked_candidates]
        new_candidate = copy.deepcopy(candidate)
        for command in candidate:
            parent_commands = templates[command]['structural_features']['context_topology']['parent_command']
            for parent_command in parent_commands:
                if parent_command not in new_candidate and parent_command in templates:
                    new_candidate.append(parent_command)
        return new_candidate

    def _param_semantic_match(self, command_node, ranked_candidates, templates=None):
        if templates is None:
            templates = self.templates
        candidate = self._get_parent_commands(ranked_candidates, templates)
        para_match = []
        for para_embedding in command_node['parameter_features']:
            para_embedding = np.array(para_embedding).reshape(1, -1)
            all_similarities = []
            for candidate_command in candidate:
                candidate_paras = templates[candidate_command]['parameter_features']
                similarities = []
                for index, candidate_para_embedding in enumerate(candidate_paras):
                    candidate_para_embedding = np.array(candidate_para_embedding).reshape(1, -1)
                    sim = cosine_similarity(para_embedding, candidate_para_embedding)
                    similarities.append((candidate_command, sim, index))
                if len(similarities) > 0:
                    all_similarities.append(sorted(similarities, key=lambda x: x[1], reverse=True)[0])
            if len(all_similarities) > 0:
                para_match.append(sorted(all_similarities, key=lambda x: x[1], reverse=True)[0])
        return para_match

    def _integrate_commands(self, best_root, ranked_candidates, para_match):
        # 带参数的配置命令映射
        if para_match:
            # print('command with parameters:')
            match_list = []
            for index, match_item in enumerate(para_match):
                # print('[parameter{}]'.format(index+1), 'correspond [parameter{}] of command -- {}'.format(match_item[2]+1, match_item[0]))
                parent_commands = self.templates[best_root][match_item[0]]["structural_features"]['context_topology']["parent_command"]
                root = parent_commands[0] if len(parent_commands)>0 else match_item[0]
                match_list.append({'para_map': [index, match_item[2]], 'trans_command': match_item[0], 'parent_command':parent_commands, 'root': root})
            return match_list
        # 不带参数命令映射
        else:
            # print('command without parameters:')
            # print('corespond command {}'.format(ranked_candidates[0][0]))
            parent_commands = self.templates[best_root][ranked_candidates[0][0]]["structural_features"]['context_topology']["parent_command"]
            root = parent_commands[0] if parent_commands else ranked_candidates[0][0]
            return [{'para_map':[], 'trans_command':ranked_candidates[0][0], 'parent_command':parent_commands, 'root': root}]

    '''def get_subtree_commands(self, root_command):
        # 返回属于该根节点的所有命令
        subtree_commands = [cmd for cmd, root in self.command2root.items() if root == root_command]
        if len(subtree_commands) == 0:
            subtree_commands = [root_command]
        return subtree_commands'''

    '''def module_match_with_score(self, src_root, src_root_semantic):
        tgt_root_names = [k for k in self.config_model.keys() if k in self.templates]
        tgt_root_embeddings = [torch.tensor(self.templates[k]['semantic_features'], dtype=torch.float32).unsqueeze(0) for k in tgt_root_names]
        tgt_root_embeddings = torch.cat(tgt_root_embeddings, dim=0).cuda()
        norm_src = torch.norm(src_root_semantic, dim=1, keepdim=True)
        norm_tgt = torch.norm(tgt_root_embeddings, dim=1, keepdim=True)
        dot_product = torch.matmul(src_root_semantic, tgt_root_embeddings.T)
        similarities = dot_product / (norm_src * norm_tgt.T)
        similarities = similarities.squeeze(0).cpu().numpy()
        best_idx = np.argmax(similarities)
        best_root = tgt_root_names[best_idx]
        similarity = similarities[best_idx]
        return best_root, similarity'''


# def _build_mapping_template_library(vendors, template_path, save_path):
#     scales = [2000, 1000, 500, 100]
#     for scale in scales:
#         command_templates = {}  # 模板库
#         configuration_matchers = {}  # 匹配器

#         for vendor in vendors:
#             vendor_templates_path = template_path.format(vendor, scale)
#             # 加载模板库
#             command_templates[vendor] = load_json_file(vendor_templates_path)
#             # 加载配置匹配器
#             configuration_matchers[vendor] = ConfigMatcher(command_templates[vendor], command_templates[vendor])

#         for vendor in vendors:
#             for target_vendor in vendors:
#                 if vendor == target_vendor:
#                     continue
#                 if (not vendor == 'Juniper') and (not target_vendor == 'Juniper'):
#                     continue
#                 command_mapping = {}
#                 # 映射每一条配置命令到目标供应商配置命令
#                 description = "Match process from {} to {}".format(vendor, target_vendor)
#                 for template, command_node in tqdm(command_templates[vendor].items(), desc=description):
#                     # print(template)
#                     matched_configuration = configuration_matchers[target_vendor].find_best_match(command_node, configuration_matchers[vendor].command2root, command_templates[vendor])
#                     command_mapping[template] = matched_configuration
#                 save_json_file(command_mapping, save_path.format(vendor, target_vendor, scale))
#                 print('Mapping template libraries {}->{} scale {} have been built and saved in {}'.format(vendor, target_vendor, scale,
#                                                                                                  save_path.format(vendor,
#                                                                                                                   target_vendor, scale)))

def _build_mapping_template_library_experiment(vendors, template_path, config_model_dir, module_match_path, save_path):
    command_templates = {}  # 模板库
    config_models = {}      # 配置模型
    command2roots = {}      # 根节点映射
    module_match = {}
    configuration_matchers = {}  # 匹配器

    for vendor in vendors:
        vendor_templates_path = template_path.format(vendor)
        vendor_config_model_path = config_model_dir.format(vendor)
        command_templates[vendor] = load_json_file(vendor_templates_path)
        config_models[vendor] = load_json_file(vendor_config_model_path)
        command2roots[vendor] = build_command2root(config_models[vendor])
        module_match[vendor] = {vendor1:load_json_file(module_match_path.format(vendor1, vendor)) 
                                for vendor1 in vendors if vendor1 != vendor}
        # print('module_match:', module_match[vendor])
        configuration_matchers[vendor] = ConfigMatcher(vendor, command_templates[vendor], config_models[vendor], module_match[vendor])

    for vendor in vendors:
        for target_vendor in vendors:
            if vendor == target_vendor:
                continue
            # if not ((vendor == 'Cisco') and (target_vendor == 'Juniper')):
            #    continue
            command_mapping = {}
            # module_match_dict = {}  # 新增：记录模块匹配信息
            description = "Match process from {} to {}".format(vendor, target_vendor)
            for src_root in command2roots[vendor].keys():
                for template, command_node in tqdm(command_templates[vendor][src_root].items(), desc=description):
                    # command_node_with_template = dict(command_node)
                    # command_node_with_template['template'] = template
                    # src_root = command2roots[vendor].get(template)
                    if src_root is None:
                        raise ValueError(f"未能在源config_model中找到{template}的根节点")
                    src_root_semantic = torch.tensor(command_templates[vendor][src_root][src_root]['semantic_features'], dtype=torch.float32).unsqueeze(0).cuda()
                    # 获取目标根节点及相似度        
                    matched_configuration, best_root = configuration_matchers[target_vendor].find_best_match(
                        vendor,
                        command_node,
                        src_root,
                        src_root_semantic
                    )
                    # 记录映射
                    if src_root not in module_match[target_vendor][vendor].keys():
                        module_match[target_vendor][vendor][src_root] = best_root
                    if not command_mapping.get(template):
                        command_mapping[template] = matched_configuration
            save_json_file(command_mapping, save_path.format(vendor, target_vendor))
            # 保存模块匹配映射
            module_match_path = save_path.format(vendor, target_vendor).replace('.json', '_module_match.json')
            save_json_file(module_match[target_vendor][vendor], module_match_path)
            print('Mapping template libraries {}->{} have been built and saved in {}'.format(
                vendor, target_vendor, save_path.format(vendor, target_vendor)))
            print('Module match mapping saved in {}'.format(module_match_path))


def _build_mapping_template_test(vendors, template_path, config_model_dir):
    command_templates = {}  # 模板库
    config_models = {}      # 配置模型
    command2roots = {}      # 根节点映射
    configuration_matchers = {}  # 匹配器
    module_match = {}  # 模块匹配

    for vendor in vendors:
        vendor_templates_path = template_path.format(vendor)
        vendor_config_model_path = config_model_dir.format(vendor)
        command_templates[vendor] = load_json_file(vendor_templates_path)
        config_models[vendor] = load_json_file(vendor_config_model_path)
        module_match[vendor] = {vendor1:load_json_file(module_match_path.format(vendor1, vendor)) 
                                for vendor1 in vendors if vendor1 != vendor}
        command2roots[vendor] = build_command2root(config_models[vendor])
        configuration_matchers[vendor] = ConfigMatcher(command_templates[vendor], config_models[vendor])

    # print(configuration_matchers['HUAWEI'].command2root['network [parameter1] [parameter2]'])
    for vendor in ['Cisco']:
        for target_vendor in ['HUAWEI']:

            command_mapping = {}
            module_match_dict = {}  # 新增：记录模块匹配信息
            description = "Match process from {} to {}".format(vendor, target_vendor)
            # for template, command_node in tqdm(command_templates[vendor].items(), desc=description):
            template = 'network [parameter1] [parameter2] area [parameter3]'
            src_root, command_node = get_root_command(command_templates[vendor], template)    # 语义节点
            # print(template)
            command_node_with_template = dict(command_node)
            command_node_with_template['template'] = template
            # src_root = command2roots[vendor].get(template)
            # root_commands = command_node_with_template['structural_features']['context_topology']['parent_command']
            # src_root = root_commands[0] if root_commands else template
            print('src_root:', src_root)
            if src_root is None:
                raise ValueError(f"未能在源config_model中找到{template}的根节点")
            src_root_semantic = torch.tensor(command_templates[vendor][src_root][src_root]['semantic_features'], dtype=torch.float32).unsqueeze(0).cuda()
            # 获取目标根节点及相似度        
            matched_configuration, best_root = configuration_matchers[target_vendor].find_best_match(
                command_node,
                src_root,
                src_root_semantic
            )
            print('matched_configuration:', matched_configuration)
            print('best_root:', best_root)
            # 记录映射
            module_match_dict[src_root] = best_root
            if not command_mapping.get(template):
                command_mapping[template] = matched_configuration

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
    # print("JSON文件已保存至{}".format(file_path))

# 从command_node获取根节点
def get_root_command(command_node, template):
    for key, value in command_node.items():
        if  template in command_node[key].keys():
            return key, command_node[key][template]

# 汇总每一个根节点中所有的配置命令
def build_command2root(tree, mapping=None):
    # 初始化
    if mapping is None:
        mapping = {}
        for key, value in tree.items():
            mapping[key] = [key]

    def collect_subcommands(subtree, root_key, mapping):
        for key, value in subtree.items():
            if key in ['template', 'command', 'explanation', 'parameters']:
                continue
            mapping[root_key].append(key)
            if isinstance(value, dict):
                collect_subcommands(value, root_key, mapping)
        return mapping
    
    for key, value in tree.items():
        mapping = collect_subcommands(value, key, mapping)
    return mapping
    

if __name__ == "__main__":
    print('加载供应商配置模板节点库, 建立相应配置匹配器')
    vendors = ["Cisco", "HUAWEI", "Juniper"]
    project_root = Path(__file__).parent.parent

    # templates_path = str(project_root / 'dataset_multi_vendor_config/config_command_node/different_scale/{}_{}.json')
    # save_path = str(project_root / 'dataset_multi_vendor_config/mapping_template_library/pre_400/{}_{}_{}.json')
    save_path = str(project_root / 'dataset_multi_vendor_config/mapping_template_library/scale400/{}_{}.json')
    templates_path = str(project_root / 'dataset_multi_vendor_config/config_command_node/scale400/{}.json')
    os.makedirs(save_path, exist_ok=True)
    # _build_juniper_400_mapping_library(vendors, templates_path, save_path)
    config_model_dir = str(project_root / 'dataset_multi_vendor_config/config_model/scale400/{}.json')
    module_match_path = str(project_root / 'dataset_multi_vendor_config/mapping_template_library/scale400/{}_{}_module_match.json')
    _build_mapping_template_library_experiment(vendors, templates_path, config_model_dir, module_match_path, save_path)
    # _build_mapping_template_test(vendors, templates_path, config_model_dir)

    '''
    command_templates = {}      # 模板库
    configuration_matchers = {}   # 匹配器
    for vendor in vendors:
        templates_path = 'config_trans/dataset_multi_vendor_config/config_command_node/{}.json'.format(vendor)
        # 加载模板库
        command_templates[vendor] = load_json_file(templates_path)
        # 加载配置匹配器
        configuration_matchers[vendor] = ConfigMatcher(command_templates[vendor])

    # test
    for template, command_node in command_templates['Cisco'].items():
        print('translate cisco configuration command:\n', template, '\nto huawei configuration command:')
        print(command_node)
        matched_configuration = configuration_matchers['HUAWEI'].find_best_match(command_node)
        print(matched_configuration[0])
    '''
