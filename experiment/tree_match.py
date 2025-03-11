# -*- coding: utf-8 -*-
"""
@Time ： 2025/3/11 14:28
@Auth ： xiaolongtuan
@File ：tree_match.py
"""

def tree_match(ref_tree: Dict[str, Any], trans_tree: Dict[str, Any]) -> float:
    """
    计算配置树匹配率（TM）。
    遍历树节点，比较标签是否一致，匹配率 = 匹配节点数 / 参考树节点总数。
    """

    def traverse(tree: Dict[str, Any]) -> List[str]:
        labels = [tree.get('label')]
        for child in tree.get('children', []):
            labels.extend(traverse(child))
        return labels

    ref_labels = traverse(ref_tree)
    trans_labels = traverse(trans_tree)

    # 统计参考树中每个标签匹配的个数
    match_count = sum(1 for label in ref_labels if label in trans_labels)
    tm_rate = match_count / len(ref_labels) if ref_labels else 0.0
    return tm_rate
