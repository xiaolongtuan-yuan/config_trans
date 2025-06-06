操作步骤：
1. 解析txt文件：[A_LLM_Parse_Config.py](A_LLM_Parse_Config.py)
    ```markdown
    nohup python -u A_LLM_Parse_Config.py --vendor HUAWEI --config_path config_data_1200 > HUAWEI1200.log 2>&1 &
    nohup python -u A_LLM_Parse_Config.py --vendor HUAWEI --config_path config_data_2000 > HUAWEI2000.log 2>&1 &
    nohup python -u A_LLM_Parse_Config.py --vendor HUAWEI --config_path config_data_2800 > HUAWEI2800.log 2>&1 &
    
    nohup python -u A_LLM_Parse_Config.py --vendor Cisco --config_path config_data_1200 > Cisco1200.log 2>&1 &
    nohup python -u A_LLM_Parse_Config.py --vendor Cisco --config_path config_data_2000 > Cisco2000.log 2>&1 &
    nohup python -u A_LLM_Parse_Config.py --vendor Cisco --config_path config_data_2800 > Cisco2800.log 2>&1 &
    
    ----------------
    nohup python -u A_LLM_Parse_Config.py --vendor Juniper --config_path config_data_1200 > Juniper1200.log 2>&1 &
    nohup python -u A_LLM_Parse_Config.py --vendor Juniper --config_path config_data_2000 > Juniper2000.log 2>&1 &
    nohup python -u A_LLM_Parse_Config.py --vendor Juniper --config_path config_data_2800 > Juniper2800.log 2>&1 &
    ```

2. 将解析后json文件简化检查并替换键值为命令模版：[B_json_simplify.py](B_json_simplify.py)
3. 构建供应商模型：[C_Model_growth.py](C_Model_growth.py)
4. 构建供应商间的命令映射，这里可以调整超参数topk=3：[E_command_match.py](E_command_match.py)
5. 进行配置的翻译：[F_new_device_configtrans.py](F_new_device_configtrans.py)
