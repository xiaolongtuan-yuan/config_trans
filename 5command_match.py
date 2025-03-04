from sklearn.metrics.pairwise import cosine_similarity
import json
import numpy as np
import copy 
from tqdm import tqdm 
'''
配置匹配器运行逻辑：
1、对比基础语义嵌入, 获取功能相似度(基础语义特征：模板、命令、解释+所有参数名与解释)
例如：
输入-->C1([p1], [p2], [p3])（原配置命令）
输出-->C2([p1], [p2]), C3([p3]) （目标配置命令候选集）

2、对比参数语义嵌入, 获取性能/结构相似度（参数语义特征：参数名/类型/解释+配置命令解释）
输入-->C1([p1], [p2], [p3]), {C2([p1], [p2]), C3([p3])}（原配置命令+目标配置命令候选集）
输出-->{C1<->p1->p1<->C2, C1<->p2->p2<->C2, C1<->p3->p3<->C3}（配置参数对）

'''

class ConfigMatcher:
    def __init__(self, target_command_templates):
        self.templates = target_command_templates  # 预加载的配置(节点)模板库
        self.semantic_topk = 3       # 语义匹配top k纳入候选集
        
    def find_best_match(self, command_node):
        """执行多级匹配流程"""
        # 第一阶段：基础语义匹配--功能匹配（计算对比所有配置节点语义嵌入排序）
        ranked_candidates = self._semantic_ranking(command_node)

        # 第二阶段：参数语义匹配--组织/结构特征（计算对比候选集中所有参数嵌入）
        para_match = self._param_semantic_match(command_node, ranked_candidates)
        
        # 第三阶段：整合匹配的参数对，并延伸至命令
        match_result = self._integrate_commands(ranked_candidates, para_match)
        
        return match_result

    def _semantic_ranking(self, command_node):
        """语义特征排序"""
        semantic_embedding = np.array(command_node['semantic_features']).reshape(1, -1)
        similarities = []
        
        for template, target_node in self.templates.items():
            target_embedding = np.array(target_node['semantic_features']).reshape(1, -1)
            sim = cosine_similarity(semantic_embedding, target_embedding)
            similarities.append((template, sim))
            
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:self.semantic_topk]

    def _get_parent_commands(self, ranked_candidates):
        # 按照配置视图层次，加入所有的父配置命令
        candidate = [candidate_command[0] for candidate_command in ranked_candidates]   # 候选配置命令模板集合
        # 递归获取所有的父配置命令
        def _parent_commands(candidate:list) -> list:
            candidate_length = len(candidate)
            for command in candidate:
                parent_command = self.templates[command]['structural_features']['context_topology']['parent_command']
                if (parent_command != 'system' and parent_command not in candidate):
                    candidate.append(parent_command)
            if candidate_length < len(candidate):
                candidate = _parent_commands(candidate)
            return candidate
        
        candidate = _parent_commands(candidate) # 补全父配置命令之后候选集
        return candidate

    def _param_semantic_match(self, command_node, ranked_candidates):
        """参数语义匹配"""
        candidate = self._get_parent_commands(ranked_candidates)
        para_match = []
        # 为command中每个参数语义需求一个最佳参数匹配
        for para_embedding in command_node['parameter_features']:
            para_embedding = np.array(para_embedding).reshape(1, -1)
            all_similarities = []
            # 对比每一个命令中的参数语义
            for candidate_command in candidate:
                candidate_paras = self.templates[candidate_command]['parameter_features']   # list
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
                match_list.append([index, match_item[2], match_item[0]])
            return match_list
        # 不带参数命令映射
        else:
            # print('command without parameters:')
            # print('corespond command {}'.format(ranked_candidates[0][0]))
            return ranked_candidates[0][0]

def _build_mapping_template_library(vendors, template_path, save_path):
    command_templates = {}      # 模板库
    configuration_matchers = {}   # 匹配器
    for vendor in vendors:
        vendor_templates_path = template_path.format(vendor)
        # templates_path = 'config_trans/dataset_multi_vendor_config/config_command_node/{}.json'.format(vendor)
        # 加载模板库
        command_templates[vendor] = load_json_file(vendor_templates_path)
        # 加载配置匹配器
        configuration_matchers[vendor] = ConfigMatcher(command_templates[vendor])
    
    for target_vendor in vendors:
        for vendor in vendors:
            if vendor == target_vendor:
                continue
            command_mapping = {}
            # 映射每一条配置命令到目标供应商配置命令
            description = "Match process from {} to {}".format(vendor, target_vendor)
            for template, command_node in tqdm(command_templates[vendor].items(), desc=description):  
                # print(template)
                matched_configuration = configuration_matchers[target_vendor].find_best_match(command_node)
                command_mapping[template] = matched_configuration
            save_json_file(command_mapping, save_path.format(vendor, target_vendor))
            print('Mapping template libraries {}->{} have been built and saved in {}'.format(vendor, target_vendor, save_path.format(vendor, target_vendor)))

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

if __name__ == "__main__":
    print('加载供应商配置模板节点库, 建立相应配置匹配器')
    vendors = ["Cisco", "HUAWEI", "Juniper"]
    templates_path = 'config_trans/dataset_multi_vendor_config/config_command_node/{}.json'
    save_path = 'config_trans/dataset_multi_vendor_config/mapping_template_library/{}_{}.json'
    _build_mapping_template_library(vendors, templates_path, save_path)
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
