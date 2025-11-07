# -*- coding: utf-8 -*-
"""
@Time ： 2025/5/29 21:09
@Auth ： xiaolongtuan
@File ：copy_tree.py
"""
import os
import shutil
from pathlib import Path


def copy_tree_skip_existing(src_dir, dst_dir):
    """
    复制目录树，跳过已存在的同名文件

    Args:
        src_dir (str): 源目录路径
        dst_dir (str): 目标目录路径
    """
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)

    # 确保目标目录存在
    dst_path.mkdir(parents=True, exist_ok=True)

    # 遍历源目录中的所有文件和文件夹
    for item in src_path.rglob('*'):
        # 计算相对路径
        relative_path = item.relative_to(src_path)
        dst_item = dst_path / relative_path

        if item.is_dir():
            # 创建目录（如果不存在）
            # dst_item.mkdir(parents=True, exist_ok=True)
            # print(f"创建目录: {dst_item}")
            continue
        else:
            # 检查文件是否已存在
            # if dst_item.exists():
            #     print(f"跳过已存在的文件: {dst_item}")
            # else:
            # 确保父目录存在
            dst_item.parent.mkdir(parents=True, exist_ok=True)
            # 复制文件
            shutil.copy2(item, dst_item)
            print(f"复制文件: {item} -> {dst_item}")


# 使用示例
if __name__ == "__main__":
    source_dir = "../experiment/test_dataset/test_data_2800"
    target_dir = "../experiment/test_dataset/all_data"

    print(f"开始复制 {source_dir} 到 {target_dir}")
    copy_tree_skip_existing(source_dir, target_dir)
    print("复制完成！")