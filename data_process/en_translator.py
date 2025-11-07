# -*- coding: utf-8 -*-
"""
@Time ： 2025/4/25 15:53
@Auth ： xiaolongtuan
@File ：en_translator.py
"""
import argostranslate.package
import argostranslate.translate
to_code = "en"
from_code = "zh"
available_packages = argostranslate.package.get_available_packages()
package_to_install = next(
    filter(lambda x: x.from_code == from_code and x.to_code == to_code, available_packages)
)
installed_packages = argostranslate.package.get_installed_packages()
if not any(pkg.from_code == from_code and pkg.to_code == to_code for pkg in installed_packages):
    argostranslate.package.install_from_path(package_to_install.download())
print('中英翻译器已加载。')

def translate_Zh2Eng(text):
    translated_text = argostranslate.translate.translate(text, from_code, to_code)
    return translated_text

if __name__ == '__main__':
    # 测试翻译功能
    text_to_translate = "你好，世界！"
    translated_text = translate_Zh2Eng(text_to_translate)
    print(f"翻译结果: {translated_text}")

    text_to_translate = "Hello, world!"
    translated_text = translate_Zh2Eng(text_to_translate)
    print(f"翻译结果: {translated_text}")

    text_to_translate = "Hello, 前进！"
    translated_text = translate_Zh2Eng(text_to_translate)
    print(f"翻译结果: {translated_text}")