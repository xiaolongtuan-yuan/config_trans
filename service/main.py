import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from service.trans_service import translate_config, config_parse, parse_json_2_visible_txt, parse_config_file

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
        json_config = json.loads(config)  # 尝试解析JSON
        source_parsed_json = parse_json_2_visible_txt(json_config)
        logging.info("Config is valid JSON")
    except json.JSONDecodeError:
        logging.warning("Config is not valid JSON")
        # 使用llm解析config
        json_config = config_parse(config, sourceVendor)
        source_parsed_json = parse_json_2_visible_txt(json_config)

    translation_result, trans_mapping_info = translate_config(json_config, sourceVendor, targetVendor, config)
    print(translation_result)

    result = TranslationResult(
        chatHistory=f"{translation_result}",
        aiExplanation=f"{source_parsed_json}",
        anotherPanel=f"{trans_mapping_info}"
    )

    return result


@app.post("/config_trans_mapping")
async def trans_mapping(input_data: ConfigInput):
    try:
        source_config_json = json.loads(input_data.config)  # 尝试解析JSON
        logging.info("Config is valid JSON")
    except json.JSONDecodeError:
        logging.warning("Config is not valid JSON")
        # 使用llm解析config
        source_config_json, tasks = parse_config_file(input_data.config, input_data.sourceVendor)
        for future, template in tasks:  # 处理LLM解析的任务
            result = future.result()
            template.update(result)

    translation_result, trans_mapping_info = translate_config(source_config_json, input_data.sourceVendor,
                                                              input_data.targetVendor, input_data.config)

    response = {
        "sourceVendor": input_data.sourceVendor,
        "sourceConfig": input_data.config,
        "targetVendor": input_data.targetVendor,
        "targetConfig": translation_result,
        "sourceCmds": trans_mapping_info["source_cmds"],
        "targetCmds": trans_mapping_info["target_cmds"],
        "edges": trans_mapping_info["edges"]
    }
    return response


if __name__ == '__main__':
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_config=None)
