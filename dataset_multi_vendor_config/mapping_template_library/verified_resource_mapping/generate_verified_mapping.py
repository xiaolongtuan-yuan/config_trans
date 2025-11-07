#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证资源映射规则生成器
根据经过工程师验证的Cisco和Huawei配置翻译对数据，生成标准化的命令映射库
包含参数位置映射和上下文信息
"""
import copy
import json
import re
import os
from typing import Dict, List, Tuple, Optional, Any
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np
from pathlib import Path


def load_json_file(file_path: str) -> Dict:
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"警告: 无法加载文件 {file_path}: {e}")
        return {}


def config_model_load(config_model_dir: str, vendors: List[str]) -> Dict:
    """
    加载配置模型
    
    Args:
        config_model_dir: 配置模型目录路径模板
        vendors: 供应商列表
        
    Returns:
        配置模型字典
    """
    config_models = {}
    for vendor in vendors:
        config_models[vendor] = load_json_file(config_model_dir.format(vendor))
        if vendor == 'Juniper':
            config_models['combined_Juniper'] = load_json_file(config_model_dir.format('Juniper_combined'))
    return config_models


class VerifiedMappingGenerator:
    """验证资源映射规则生成器"""

    def __init__(self, config_model_dir: str = None, vendors: List[str] = None):
        """
        初始化生成器
        
        Args:
            config_model_dir: 配置模型目录路径模板
            vendors: 供应商列表
        """
        if config_model_dir and vendors:
            self.config_models = config_model_load(config_model_dir, vendors)
        else:
            self.config_models = {}

        # 使用项目中的相对路径
        self.embedding_model = SentenceTransformer('EmbeddingModel/MiniLM-L6-v2')

    def find_template(self, command: str, config_model: Dict) -> Optional[Dict]:
        """
        在配置模型中查找命令模板
        
        Args:
            command: 原始命令
            config_model: 配置模型字典
            
        Returns:
            匹配的模板字典或None
        """
        for template, details in config_model.items():
            if isinstance(details, dict) and 'template' in details:
                # 递归查找子模板
                sub_template = self.find_template(command, details)
                if sub_template:
                    return sub_template

                # 使用正则表达式匹配模板
                pattern = re.sub(r"\[[^\]]+\]", r'(\\S+)', details['template'])
                pattern = f'^{pattern}$'
                try:
                    match = re.match(pattern, command)
                    if match:
                        # 提取参数值
                        param_values = match.groups()

                        # 复制原始参数信息并更新value值
                        updated_parameters = []
                        original_params = details.get('parameters', [])

                        for i, param in enumerate(original_params):
                            updated_param = param.copy()
                            if i < len(param_values):
                                updated_param['value'] = param_values[i]
                            updated_parameters.append(updated_param)

                        return {
                            "template": details['template'],
                            "command": command,
                            "explanation": details['explanation'],
                            "parameters": updated_parameters,
                        }
                    else:
                        continue
                except re.error:
                    continue
        return None

    def _match_template(self, command: str, template: str) -> bool:
        """
        检查命令是否匹配模板
        
        Args:
            command: 实际命令
            template: 模板字符串
            
        Returns:
            是否匹配
        """
        # 将模板中的参数占位符替换为正则表达式
        pattern = re.escape(template)
        pattern = pattern.replace(r'\[parameter\d+\]', r'[^\s]+')
        pattern = f'^{pattern}$'

        return bool(re.match(pattern, command))

    def parse_command_to_template(self, command: str) -> Dict:
        """
        将具体命令解析为模板格式
        
        Args:
            command: 具体的命令字符串
            
        Returns:
            包含模板信息的字典
        """
        # 提取参数
        parameters = []
        template = command

        # 常见的参数模式
        patterns = [
            (r'\b\d+\.\d+\.\d+\.\d+\b', 'IPv4'),  # IP地址
            (r'\b\d+\b', 'integer'),  # 数字
            (r'\b[A-Za-z][A-Za-z0-9_-]*\b', 'string'),  # 标识符
        ]

        param_count = 0
        for pattern, param_type in patterns:
            matches = list(re.finditer(pattern, command))
            for match in reversed(matches):  # 从后往前替换，避免位置偏移
                param_name = f"parameter{param_count + 1}"
                parameters.append({
                    "name": param_name,
                    "type": param_type,
                    "value": match.group(),
                    "position": param_count
                })
                template = template[:match.start()] + f"[{param_name}]" + template[match.end():]
                param_count += 1

        return {
            "template": template,
            "command": command,
            "explanation": f"解析的命令: {command}",
            "parameters": parameters
        }

    def extract_parameters_from_commands(self, source_template_info, target_template_info_list) -> List[List[int]]:
        """
        通过相似度匹配提取参数映射关系
        参考src/E_command_match.py中的参数映射逻辑
        
        Args:
            source_template_info: 源命令模板信息
            target_template_info_list: 目标命令模板信息列表
        
        Returns:
            参数映射列表 [[source_param_idx, target_param_idx, target_template_idx], ...]
        """
        para_map = []
        source_params = source_template_info.get('parameters', [])

        if not source_params:
            for target_template_idx, target_template_info in enumerate(target_template_info_list):
                para_map.append({
                    "para_map": [],
                    "trans_command": target_template_info.get("template"),
                    "parent_command": [],
                    "root": '',
                })
            return para_map

        # 为每个源参数生成语义嵌入并找到最佳匹配
        for source_param_idx, source_param in enumerate(source_params):
            # 生成源参数的语义嵌入
            source_para_text = (
                    source_param.get('value', '') +
                    source_param.get('name', '') +
                    source_param.get('explanation', '') +
                    source_template_info.get('template', '')
            )
            source_para_embedding = self.embedding_model.encode([source_para_text])

            all_similarities = []

            # 遍历所有目标模板
            for target_template_idx, target_template_info in enumerate(target_template_info_list):
                target_params = target_template_info.get('parameters', [])

                # 为目标模板的每个参数计算相似度
                for target_param_idx, target_param in enumerate(target_params):
                    # 生成目标参数的语义嵌入
                    target_para_text = (
                            target_param.get('value', '') +
                            target_param.get('name', '') +
                            target_param.get('explanation', '') +
                            target_template_info.get('template', '')
                    )
                    target_para_embedding = self.embedding_model.encode([target_para_text])

                    # 计算余弦相似度
                    similarity = cosine_similarity(source_para_embedding, target_para_embedding)[0][0]

                    all_similarities.append({
                        'similarity': similarity,
                        'trans_command': target_template_info.get('template', ''),
                        'target_param_idx': target_param_idx
                    })

            # 找到相似度最高的匹配
            if all_similarities:
                best_match = max(all_similarities, key=lambda x: x['similarity'])

                # 构建标准化映射条目
                standardized_entry = {
                    "para_map": [source_param_idx, best_match['target_param_idx']],
                    "trans_command": best_match['trans_command'],
                    "parent_command": [],
                    "root": ''
                }
                para_map.append(standardized_entry)

        return para_map

    def process_verified_rules(self, verified_rules_path: str, source_vendor: str = "Cisco",
                               target_vendor: str = "Huawei") -> Dict:
        """
        处理验证的规则文件，生成标准化映射
        
        Args:
            verified_rules_path: 验证规则文件路径
            source_vendor: 源供应商名称
            
        Returns:
            标准化的映射字典
        """
        # 加载验证规则
        verified_rules = load_json_file(verified_rules_path)

        standardized_mapping = {}

        for source_command_str, mappings in verified_rules.items():
            source_command_list = list(map(str.strip, source_command_str.strip().split('\n')))
            for source_command in source_command_list:
                source_template_info = self.find_template(source_command, self.config_models[source_vendor])
                if not source_template_info:
                    source_template_info = {'command': source_command,
                                            'explanation': '',
                                            'parameters': [],
                                            'template': source_command}
                mapping = mappings[0]
                target_command_str = mapping.get('trans_command', '')
                target_command_list = list(map(str.strip, target_command_str.strip().split('\n')))
                target_template_info_list = []
                for target_command in target_command_list:
                    # 解析源命令和目标命令为模板
                    target_template_info = self.find_template(target_command,
                                                              self.config_models[target_vendor])  # 暂时就不添加parant了
                    if not target_template_info:
                        target_template_info = {'command': target_command,
                                                'explanation': '',
                                                'parameters': [],
                                                'template': target_command}
                    target_template_info_list.append(target_template_info)

                # 提取参数映射
                para_map = self.extract_parameters_from_commands(source_template_info, target_template_info_list)
                # 使用模板作为键
                template_key = copy.deepcopy(source_template_info.get('template', source_command))
                standardized_mapping[template_key] = copy.deepcopy(para_map)

        return standardized_mapping

    def process_verified_rules_inverse(self, verified_rules_path: str, source_vendor: str = "Huawei",
                                       target_vendor: str = "Cisco") -> Dict:
        """
        处理验证的规则文件，生成标准化映射

        Args:
            verified_rules_path: 验证规则文件路径
            source_vendor: 源供应商名称

        Returns:
            标准化的映射字典
        """
        # 加载验证规则
        verified_rules = load_json_file(verified_rules_path)

        standardized_mapping = {}

        for target_command_str, mappings in verified_rules.items():
            target_command_list = list(map(str.strip, target_command_str.strip().split('\n')))
            mapping = mappings[0]
            source_command_str = mapping.get('trans_command', '')
            source_command_list = list(map(str.strip, source_command_str.strip().split('\n')))

            for source_command in source_command_list:
                source_template_info = self.find_template(source_command, self.config_models[source_vendor])
                if not source_template_info:
                    source_template_info = {'command': source_command,
                                            'explanation': '',
                                            'parameters': [],
                                            'template': source_command}

                target_template_info_list = []
                for target_command in target_command_list:
                    # 解析源命令和目标命令为模板
                    target_template_info = self.find_template(target_command,
                                                              self.config_models[target_vendor])  # 暂时就不添加parant了
                    if not target_template_info:
                        target_template_info = {'command': target_command,
                                                'explanation': '',
                                                'parameters': [],
                                                'template': target_command}
                    target_template_info_list.append(target_template_info)

                # 提取参数映射
                para_map = self.extract_parameters_from_commands(source_template_info, target_template_info_list)
                # 使用模板作为键
                template_key = source_template_info.get('template', source_command)
                standardized_mapping[template_key] = copy.deepcopy(para_map)

        return standardized_mapping

    def _calculate_mapping_confidence(self, source_cmd: str, target_cmd: str) -> float:
        """
        计算映射的置信度
        
        Args:
            source_cmd: 源命令
            target_cmd: 目标命令
            
        Returns:
            置信度分数 (0-1)
        """
        # 使用语义相似度作为置信度指标
        try:
            source_embedding = self.embedding_model.encode([source_cmd])
            target_embedding = self.embedding_model.encode([target_cmd])
            similarity = cosine_similarity(source_embedding, target_embedding)[0][0]
            return float(similarity)
        except:
            return 0.5  # 默认置信度

    def validate_mapping_rules(self, mapping_dict: Dict) -> Dict:
        """
        验证映射规则的合理性
        
        Args:
            mapping_dict: 映射字典
            
        Returns:
            验证后的映射字典
        """
        validated_mapping = {}

        for source_template, mappings in mapping_dict.items():
            validated_mappings = []

            for mapping in mappings:
                # 检查参数映射的合理性
                para_map = mapping.get('para_map', [])
                if self._validate_parameter_mapping(para_map, source_template, mapping.get('trans_command', '')):
                    validated_mappings.append(mapping)
                else:
                    print(f"警告: 参数映射不合理 - {source_template} -> {mapping.get('trans_command', '')}")

            if validated_mappings:
                validated_mapping[source_template] = validated_mappings

        return validated_mapping

    def _validate_parameter_mapping(self, para_map: List, source_template: str, target_template: str) -> bool:
        """
        验证参数映射的合理性
        
        Args:
            para_map: 参数映射列表
            source_template: 源模板
            target_template: 目标模板
            
        Returns:
            映射是否合理
        """
        # 计算模板中的参数数量
        source_param_count = len(re.findall(r'\[parameter\d+\]', source_template))
        target_param_count = len(re.findall(r'\[parameter\d+\]', target_template))

        # 检查参数映射索引是否在合理范围内
        for mapping in para_map:
            if len(mapping) != 2:
                return False
            source_idx, target_idx = mapping
            if source_idx >= source_param_count or target_idx >= target_param_count:
                return False
            if source_idx < 0 or target_idx < 0:
                return False

        return True

    def generate_mapping_library(self,
                                 verified_rules_path: str,
                                 output_path: str,
                                 source_vendor: str = "Cisco",
                                 target_vendor: str = "HUAWEI") -> None:
        """
        生成完整的映射库
        
        Args:
            verified_rules_path: 验证规则文件路径
            output_path: 输出文件路径
            source_vendor: 源供应商
            target_vendor: 目标供应商
        """
        print(f"开始处理 {source_vendor} -> {target_vendor} 映射规则...")

        # 处理验证规则
        standardized_mapping = self.process_verified_rules(verified_rules_path, source_vendor, target_vendor)
        standardized_mapping_inverse = self.process_verified_rules_inverse(verified_rules_path, target_vendor,
                                                                           source_vendor)
        print(f"处理了 {len(standardized_mapping)} 个命令映射")

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 保存映射库
        with open(output_path.format(source_vendor, target_vendor), 'w', encoding='utf-8') as f:
            json.dump(standardized_mapping, f, ensure_ascii=False, indent=2)

        with open(output_path.format(target_vendor, source_vendor), 'w', encoding='utf-8') as f:
            json.dump(standardized_mapping_inverse, f, ensure_ascii=False, indent=2)

        # 生成统计报告
        # self._generate_statistics_report(validated_mapping, output_path.replace('.json', '_stats.txt'))

    def _generate_statistics_report(self, mapping_dict: Dict, report_path: str) -> None:
        """
        生成统计报告
        
        Args:
            mapping_dict: 映射字典
            report_path: 报告文件路径
        """
        total_commands = len(mapping_dict)
        total_mappings = sum(len(mappings) for mappings in mapping_dict.values())

        # 计算置信度分布
        confidences = []
        for mappings in mapping_dict.values():
            for mapping in mappings:
                confidences.append(mapping.get('confidence', 0.5))

        avg_confidence = np.mean(confidences) if confidences else 0

        # 统计参数映射情况
        param_mapping_stats = {
            'with_params': 0,
            'without_params': 0,
            'complex_mappings': 0  # 一对多映射
        }

        for mappings in mapping_dict.values():
            if len(mappings) > 1:
                param_mapping_stats['complex_mappings'] += 1

            for mapping in mappings:
                if mapping.get('para_map'):
                    param_mapping_stats['with_params'] += 1
                else:
                    param_mapping_stats['without_params'] += 1

        # 写入报告
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("验证资源映射库统计报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"总命令数: {total_commands}\n")
            f.write(f"总映射数: {total_mappings}\n")
            f.write(f"平均置信度: {avg_confidence:.3f}\n\n")
            f.write("参数映射统计:\n")
            f.write(f"  包含参数映射: {param_mapping_stats['with_params']}\n")
            f.write(f"  无参数映射: {param_mapping_stats['without_params']}\n")
            f.write(f"  复杂映射(一对多): {param_mapping_stats['complex_mappings']}\n")


def main():
    """主函数"""
    # 配置路径
    verified_rules_path = "dataset_multi_vendor_config/verified_resources/rule.json"
    output_path = "dataset_multi_vendor_config/mapping_template_library/verified_resource_mapping/{}_{}.json"
    config_model_dir = "dataset_multi_vendor_config/mapping_template_library/verified_resource_mapping/temp_expansion/{}.json"
    vendors = ["Cisco", "HUAWEI"]

    # 创建生成器实例
    generator = VerifiedMappingGenerator(config_model_dir, vendors)

    # 生成映射库
    generator.generate_mapping_library(
        verified_rules_path=verified_rules_path,
        output_path=output_path,
        source_vendor="Cisco",
        target_vendor="HUAWEI"
    )

    print("映射库生成完成!")


if __name__ == "__main__":
    main()
