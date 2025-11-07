# -*- coding: utf-8 -*-
"""
华为翻译工具效果评估脚本
参考 table_ours_and_rag.py 的评估方法
"""
import json
import os
import sys

sys.path.append("/data/zy/projects/config_trans")
import experiment

from experiment.compute_bleu import compute_embded_similarity
from experiment.syntax_correctness import load_config_model, cul_view_accuracy
from experiment.tree_match import cul_command_accuracy, cul_grammatical_accuracy, cul_param_accuracy, \
    cul_grammatical_accuracy_with_json, cul_device_grammatical_accuracy_with_json, cul_command_and_param_accuracy, \
    cuL_llm_accuracy_with_json, cuL_llm_coverage_with_json

def evaluate_huawei_translation():
    """评估华为翻译工具的效果"""
    
    # 配置路径
    translated_config_dir = 'experiment/exper_data/huawei_trans_test/cisco-huawei'  # 华为翻译工具输出
    real_config_dir = 'experiment/exper_data/huawei_trans_test/HUAWEI'  # 真实标签
    config_model_path = 'dataset_multi_vendor_config/config_model/all_data_2800/HUAWEI.json'  # 华为配置模型
    
    # 检查目录是否存在
    if not os.path.exists(translated_config_dir):
        print(f"错误：翻译输出目录不存在: {translated_config_dir}")
        return
    
    if not os.path.exists(real_config_dir):
        print(f"错误：真实标签目录不存在: {real_config_dir}")
        return
    
    if not os.path.exists(config_model_path):
        print(f"错误：配置模型文件不存在: {config_model_path}")
        return
    
    # 获取配置文件列表
    translated_files = [f for f in os.listdir(translated_config_dir) if f.endswith('.txt')]
    real_files = [f for f in os.listdir(real_config_dir) if f.endswith('.txt')]
    
    # 找到共同的文件（确保有对应的标签）
    common_files = list(set(translated_files) & set(real_files))
    
    if not common_files:
        print("错误：没有找到匹配的配置文件")
        return
    
    print(f"找到 {len(common_files)} 个匹配的配置文件")
    
    # 加载华为配置模型
    config_model = load_config_model(config_model_path)
    
    # 初始化评估结果
    evaluation_results = {
        "semantic_similarity": 0,
        "command_accuracy": 0,
        "param_accuracy": 0,
        "grammatical_accuracy": 0,
        "view_accuracy": 0,
        "total_files": len(common_files),
        "evaluated_files": []
    }
    
    print("开始评估华为翻译工具效果...")
    
    # 1. 计算语义相似度
    print("计算语义相似度...")
    try:
        semantic_similarity = compute_embded_similarity(
            translated_config_dir, real_config_dir, common_files
        )
        evaluation_results["semantic_similarity"] = semantic_similarity
        print(f"语义相似度: {semantic_similarity:.4f}")
    except Exception as e:
        print(f"计算语义相似度时出错: {e}")
        evaluation_results["semantic_similarity"] = 0
    
    # 2. 计算命令准确率
    print("计算命令准确率...")
    try:
        command_accuracy = cul_command_accuracy(
            translated_config_dir, real_config_dir, common_files
        )
        evaluation_results["command_accuracy"] = command_accuracy
        print(f"命令准确率: {command_accuracy:.4f}")
    except Exception as e:
        print(f"计算命令准确率时出错: {e}")
        evaluation_results["command_accuracy"] = 0
    
    # 3. 计算参数准确率
    print("计算参数准确率...")
    try:
        param_accuracy = cul_param_accuracy(
            translated_config_dir, real_config_dir, common_files, config_model
        )
        evaluation_results["param_accuracy"] = param_accuracy
        print(f"参数准确率: {param_accuracy:.4f}")
    except Exception as e:
        print(f"计算参数准确率时出错: {e}")
        evaluation_results["param_accuracy"] = 0
    
    # 4. 计算语法正确性
    print("计算语法正确性...")
    try:
        grammatical_accuracy = cul_grammatical_accuracy(
            translated_config_dir, real_config_dir, common_files, config_model
        )
        evaluation_results["grammatical_accuracy"] = grammatical_accuracy
        print(f"语法正确性: {grammatical_accuracy:.4f}")
    except Exception as e:
        print(f"计算语法正确性时出错: {e}")
        evaluation_results["grammatical_accuracy"] = 0
    
    # 5. 计算视图准确率
    print("计算视图准确率...")
    try:
        view_accuracy = cul_view_accuracy(
            translated_config_dir, common_files, config_model
        )
        evaluation_results["view_accuracy"] = view_accuracy
        print(f"视图准确率: {view_accuracy:.4f}")
    except Exception as e:
        print(f"计算视图准确率时出错: {e}")
        evaluation_results["view_accuracy"] = 0
    
    # 记录评估的文件
    evaluation_results["evaluated_files"] = common_files
    
    # 保存评估结果
    output_file = 'experiment/exper_res/huawei_translation_evaluation.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluation_results, f, indent=4, ensure_ascii=False)
    
    print(f"\n评估完成！结果已保存到: {output_file}")
    print("\n=== 华为翻译工具评估结果 ===")
    print(f"评估文件数量: {evaluation_results['total_files']}")
    print(f"语义相似度: {evaluation_results['semantic_similarity']:.4f}")
    print(f"命令准确率: {evaluation_results['command_accuracy']:.4f}")
    print(f"参数准确率: {evaluation_results['param_accuracy']:.4f}")
    print(f"语法正确性: {evaluation_results['grammatical_accuracy']:.4f}")
    print(f"视图准确率: {evaluation_results['view_accuracy']:.4f}")
    
    return evaluation_results

if __name__ == '__main__':
    evaluate_huawei_translation()


