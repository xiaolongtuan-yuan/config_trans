import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from service.trans_service import translate_config, config_parse, parse_json_2_visible_txt

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定允许的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求体模型，接收配置内容和目标供应商
class ConfigInput(BaseModel):
    config: str
    sourceVendor: str
    targetVendor: str

# 响应模型，包含三个字段
class TranslationResult(BaseModel):
    chatHistory: str
    aiExplanation: str
    anotherPanel: str

@app.post("/config_trans", response_model=TranslationResult)
async def config_trans(input_data: ConfigInput):
    logging.info(f"Received input data: {input_data}")
    # 根据目标供应商，可以在这里加入不同的翻译逻辑
    sourceVendor = input_data.sourceVendor
    targetVendor = input_data.targetVendor
    config = input_data.config
    try:
        config = json.loads(config)  # 尝试解析JSON
        source_parsed_json = parse_json_2_visible_txt(config)
        logging.info("Config is valid JSON")
    except json.JSONDecodeError:
        logging.warning("Config is not valid JSON")
        # 使用llm解析config
        config = config_parse(config, sourceVendor)
        source_parsed_json = parse_json_2_visible_txt(config)

    translation_result, trans_mapping_info = translate_config(config, sourceVendor, targetVendor)
    print(translation_result)

    result = TranslationResult(
        chatHistory=f"{translation_result}",
        aiExplanation=f"{source_parsed_json}",
        anotherPanel=f"{trans_mapping_info}"
    )
    return result

if __name__ == '__main__':
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_config=None)