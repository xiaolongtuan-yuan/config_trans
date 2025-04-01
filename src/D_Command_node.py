from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
import torch
import json
import warnings

from tqdm import tqdm

warnings.filterwarnings("ignore", category=UserWarning, module="torch")


# 输入----
# Command_nodes= {'command_template': CommandNode_Object}
# config_model-->供应商大配置模型
# parent_command-->父节点配置命令
# depth_commmand-->配置命令层级
# 输出---
# Command_Nodes
def parse_command_node(Command_nodes: dict, config_model: dict, embedding_model, parent_command='system', depth=0):
    for k, sub_dict in config_model.items():
        if not isinstance(sub_dict, dict):
            continue

        if k in Command_nodes:
            # k已将在Command_nodes中了，我们的策略是保留depth最小的节点，保证语法正确性
            if Command_nodes[k]['structural_features']['command_depth'] <= depth:
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

            # 创建命令节点
            if run_type == 'main':
                # 其次为语义特征（包括template/command/explanation/parameters）
                command_example = sub_dict["command"] if sub_dict.get("command") else ''
                command_explanation = sub_dict["explanation"] if sub_dict.get("explanation") else ''
                semantic_feature = {'template': sub_dict['template'],
                                    'command': command_example,
                                    'explanation': command_explanation,
                                    'parameters': command_parameters}

                command_node = CommandNode(structural_feature, semantic_feature, embedding_model)
            elif run_type == 'debug':
                command_node = CommandNode(structural_feature, {}, embedding_model)
            else:
                raise ValueError('run_type error')

            Command_nodes[k] = {'structural_features': command_node.structural_features,
                                'semantic_features': command_node.semantic_features,
                                'parameter_features': command_node.paras_semantic_features}
            # print(k)
            # break

        '''for child_k, child_v in sub_dict.items():
            if not isinstance(child_v, dict):
                continue'''
        parse_command_node(Command_nodes, sub_dict, embedding_model, k, depth + 1)

    return Command_nodes


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

        if run_type == 'main':
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
            para_text = p['name'] + p['explanation'] + semantic_features['template']     # + semantic_features['explanation']
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


def main():
    project_root = Path(__file__).parent.parent
    # 加载embedding model
    local_EMmodel_path = str(project_root / 'EmbeddingModel/MiniLM-L6-v2')
    # embedding_model = SentenceTransformer(local_EMmodel_path)
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path)

    vendors = ["Juniper"]
    config_num = [100, 500, 1000, 2000]

    # vendors = ["HUAWEI"]
    for vendor in vendors:
        for num in config_num:
            Command_nodes = {}  # 'command_template': CommandNode_Object
            config_model_path = str(project_root / f'dataset_multi_vendor_config/config_model/different_scale/{vendor}_{num}.json')

            # 加载供应商配置模型
            config_model = load_json_file(config_model_path)
            # 解析配置节点
            Command_nodes = parse_command_node(Command_nodes, config_model, embedding_model)
            # 保存配置节点（json）
            save_path = str(project_root / f'dataset_multi_vendor_config/config_command_node/different_scale/{vendor}_{num}.json')
            save_json_file(Command_nodes, save_path)
            print(f"finished {vendor} with {num} scales")

            # save_path = str(project_root / 'dataset_multi_vendor_config/config_command_node_debug/{}.json'.format(vendor))
            # save_json_file(Command_nodes, save_path)

def debug():
    project_root = Path(__file__).parent.parent
    # 加载embedding model
    local_EMmodel_path = str(project_root / 'EmbeddingModel/MiniLM-L6-v2')
    # embedding_model = SentenceTransformer(local_EMmodel_path)
    embedding_model = HuggingFaceEmbeddings(model_name=local_EMmodel_path)

    vendors = ["Juniper"]
    config_num = [100,500,1000,2000]
    # vendors = ["HUAWEI"]
    for vendor in vendors:
        for num in config_num:
            Command_nodes = {}  # 'command_template': CommandNode_Object
            config_model_path = str(project_root / f'dataset_multi_vendor_config/config_model/different_scale/{vendor}_{num}.json')

            # 加载供应商配置模型
            config_model = load_json_file(config_model_path)
            # 解析配置节点
            Command_nodes = parse_command_node(Command_nodes, config_model, embedding_model)

            save_path = str(project_root / f'dataset_multi_vendor_config/config_command_node_debug/different_scale/{vendor}_{num}.json')
            save_json_file(Command_nodes, save_path)
            print(f"finished {vendor} with {num} scales")

if __name__ == "__main__":
    run_type = 'main'

    if run_type == 'main':
        main()
    if run_type == 'debug':
        debug()



