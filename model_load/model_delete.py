from transformers.utils import logging
from transformers import AutoModelForCausalLM

logging.set_verbosity_info()  # 启用详细日志
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
print(model.config._name_or_path)  # 打印模型缓存路径

import shutil
# cache_dir = "~/.cache/huggingface/transformers"  # 默认缓存路径
# shutil.rmtree(cache_dir)  # 删除整个缓存目录