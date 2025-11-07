# -*- coding: utf-8 -*-
"""
@Time ： 2025/6/3 14:57
@Auth ： xiaolongtuan
@File ：trans_node.py
"""

class TransCommandNodeContext:
    def __init__(self, template, command, explanation, parameters):
        self.template = template
        self.command = command
        self.explanation = explanation
        self.parameters = parameters
        self.children = {}
        self.parent = None
        self.depth = 0
        self.structural_feature = None
        self.semantic_feature = None
        self.match = []
        self.root = None
        self.para_list = None
        self.target_command = {}

    def set_structural_feature(self,structural_feature):
        self.structural_feature = structural_feature

    def set_parent(self, parent):
        self.parent = parent

    def set_root(self, root):
        self.root = root

    def set_depth(self, depth):
        self.depth = depth

    def add_child(self, child):
        self.children[child.command] = child

    def set_structural_features(self, structural_feature):
        self.structural_features = structural_feature

    def set_semantic_features(self, semantic_feature):
        self.semantic_features = semantic_feature

    def set_match(self, match):
        self.match = match

    def set_para_list(self, para_list):
        # if len(para_list) != len(self.parameters):
        #     raise ValueError("para_list length not equal to parameters length")
        # else:
        self.para_list = para_list