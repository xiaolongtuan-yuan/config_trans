```markdown
nohup python -u A_LLM_Parse_Config.py HUAWEI config_data_1-400 > HUAWEI.log 2>&1 &

nohup python -u A_LLM_Parse_Config.py Cisco config_data_1-400 > Cisco.log 2>&1 &

----------------
nohup python -u A_LLM_Parse_Config.py Juniper config_data_1-400 > Juniper1_400.log 2>&1 &

nohup python -u A_LLM_Parse_Config.py Juniper config_data_401-800 > Juniper401_800.log 2>&1 &

nohup python -u A_LLM_Parse_Config.py Juniper config_data_801-1200 > Juniper801_1200.log 2>&1 &

nohup python -u A_LLM_Parse_Config.py Juniper config_data_1600_1999 > Juniper1600_1999.log 2>&1 &

nohup python -u A_LLM_Parse_Config.py Juniper config_data_2400-2889 > Juniper2400_2889.log 2>&1 &

```