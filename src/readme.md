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