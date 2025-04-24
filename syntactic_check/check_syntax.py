'''from napalm import get_network_driver
from napalm.base.exceptions import MergeConfigException

driver = get_network_driver('ios')  # 或 'junos' 等
dev = driver('10.0.0.1', 'user', 'pass')
dev.open()
try:
    dev.load_merge_candidate(config="interface GigabitEthernet0/1\n no shutdown\n")
    print("语法正确")
except MergeConfigException as e:
    print("语法错误：", e)'''
import os
from pybatfish.client.session import Session
import json

# 连接到本地运行的 Batfish 服务
bf = Session(host="localhost", port=9996)

def syntax_verify(bf, config_file_path):
    # 为待分析的配置定义一个逻辑网络名称
    bf.set_network("my-network")
    try:
        # 添加异常捕获
        bf.init_snapshot(config_file_path, name="snap1", overwrite=True)
    except Exception as e:
        # 记录错误文件名到日志
        with open("batfish_errors.log", "a") as f:
            f.write(f"Failed config: {config_file_path}\n")
            f.write(f"Error message: {str(e)}\n\n")
        # 直接返回失败状态和错误类型
        return False, {'syntax': False, 'error_type': 'init_failed', 'message': str(e)}

    # 3. 查询并打印语法解析状态
    parse_status_df = bf.q.fileParseStatus().answer().frame()
    # print("=== 解析状态 ===")
    print(parse_status_df)

    if parse_status_df.at[0, 'Status'] == 'PASSED':
        return True,  {'syntax':True}
    else:
        # 4. 若有警告，查询并打印
        warnings_df = bf.q.parseWarning().answer().frame()
        # print("\n=== 解析警告 ===")
        print(warnings_df)

    return False,  {'syntax':False, 'line':list(warnings_df['Line']), 
                               'text':list(warnings_df['Text']), 'comment': list(warnings_df['Comment'])}



# 遍历源文件夹下所有.txt文件
for vendor in ['Cisco', 'Juniper']:
    error_command_dic = {}
    # 源文件夹和
    source_folder = f'config_trans/dataset_multi_vendor_config/config_data_1-400/Juniper/'
    for filename in os.listdir(source_folder):
        if filename.endswith('.txt'):
            # 待检测的配置文件cfg
            config_file_path = f'syntactic_check/config_data_400/{vendor}_config/{vendor}_{os.path.splitext(filename)[0]}/'
            pass_flag, error_command = syntax_verify(bf, config_file_path)
            if not pass_flag: 
                error_command_dic[filename] = error_command
                # print(error_command_dic, '\n', error_command)
    print(len(list(error_command_dic.keys())))
    save_path = f'syntactic_check/error_info/{vendor}_error_syntax.json'
    with open(save_path, 'w', encoding='utf-8') as json_file:
        # json.dump(data, json_file, indent=4)
        json.dump(error_command_dic, json_file, ensure_ascii=False, indent=4)
    print(f'配置语法检测结果保存至{save_path}')