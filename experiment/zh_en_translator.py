# 安装依赖
# pip install googletrans==4.0.0-rc1

import argostranslate.package
import argostranslate.translate
import json
from pathlib import Path

# 下载并安装语言包（如英语→中文）
to_code = "en"
from_code = "zh"
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()
package_to_install = next(
    filter(lambda x: x.from_code == from_code and x.to_code == to_code, available_packages)
)
argostranslate.package.install_from_path(package_to_install.download())
print('中英翻译器已加载。')
# 执行翻译
# translated_text = argostranslate.translate.translate("你好，世界", from_code, to_code)
# print(translated_text)  # 输出：hello, world


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


# 遍历配置模型中的每一个节点，翻译explanation，中文翻译英文
def trans_zh_en_explanation(config_model: dict):
    for k, sub_dict in config_model.items():
        
        if not isinstance(sub_dict, dict):
            continue
        else:
            template_key = sub_dict.get("template")
            explanation_key = sub_dict.get("explanation")
            parameters_key = sub_dict.get("parameters")

            if explanation_key:
                print(sub_dict['explanation'])
                translated_text = argostranslate.translate.translate(sub_dict['explanation'], from_code, to_code)
                sub_dict['explanation'] = translated_text
                print(sub_dict['explanation'])
            if parameters_key:
                for parameter in sub_dict['parameters']:
                    print(parameter['explanation'])
                    translated_text = argostranslate.translate.translate(parameter['explanation'], from_code, to_code)
                    parameter['explanation'] = translated_text
                    print(parameter['explanation'])
        trans_zh_en_explanation(sub_dict)

    return config_model

vendors = ["Cisco", "HUAWEI"]
project_root = Path(__file__).parent.parent

for vendor in vendors:
    for file in ['config_model', 'command_tree']:

        vendor_model_path = f'experiment/test_dataset/command_tree/{vendor}/{file}.json'
        vendor_model_path_en = str(project_root / f'scale388en/{vendor}_en.json')
        vendor_model = load_json_file(vendor_model_path)
        print('开始翻译：')
        vendor_model = trans_zh_en_explanation(vendor_model)
        save_json_file(vendor_model, vendor_model_path_en)