import os
from pybatfish.client.session import Session
import json
import shutil
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



def batch_syntax(range_num):
    # range_num = '400'
    # range_num = '1200'
    # range_num = '2000'
    # range_num = '2800'
    # 遍历源文件夹下所有.txt文件
    for vendor in ['Cisco', 'Juniper']:
        error_command_dic = {}
        # 源文件夹
        source_folder = f'syntactic_check/config_data_{range_num}/{vendor}_config/'
        for filename in os.listdir(source_folder):
            config_name = filename.replace(f"{vendor}_", "")
            # 待检测的配置文件cfg
            config_file_path = f'syntactic_check/config_data_{range_num}/{vendor}_config/{filename}/'
            pass_flag, error_command = syntax_verify(bf, config_file_path)
            if not pass_flag: 
                error_command_dic[config_name+'.txt'] = error_command 
                # print(error_command_dic, '\n', error_command)
        print(len(list(error_command_dic.keys())))
        save_dir = f'syntactic_check/config_data_{range_num}/error_info/'
        # 确保目标文件夹存在
        os.makedirs(save_dir, exist_ok=True)
        save_path = save_dir + f'{vendor}_error_syntax.json'
        with open(save_path, 'w', encoding='utf-8') as json_file:
            # json.dump(data, json_file, indent=4)
            json.dump(error_command_dic, json_file, ensure_ascii=False, indent=4)
        print(f'配置语法检测结果保存至{save_path}')

def single_syntax():
    config_file_path = f'test_config/'
    pass_flag, error_command = syntax_verify(bf, config_file_path)
    print('pass_flag:', pass_flag, '\n',
          'error_command:', error_command)
    
def collect_test_dataset(range_num):
    vendors = ['Cisco', 'HUAWEI', 'Juniper']
    # 加载配置pass file 列表
    file_names_path = f'./config_data_{range_num}/error_info/config_summary.json'
    with open(file_names_path, 'r', encoding='utf-8') as json_file:
        file_names = json.load(json_file)["test_config"]['config']
    # 复制移动测试数据, cfg-->txt    
    for vendor in vendors:
        for file_name in file_names:
            # 源数据路径
            source_folder = f'./config_data_{range_num}/{vendor}_config/'
            source_file_path = f'{vendor}_{os.path.splitext(file_name)[0]}/configs/{os.path.splitext(file_name)[0]}.cfg'
            # 目标文件夹
            target_folder = f'./test_dataset_{range_num}/{vendor}/'
            os.makedirs(target_folder, exist_ok=True)
            source_path = os.path.join(source_folder, source_file_path)
            target_path = os.path.join(target_folder, file_name)
            # 复制并改名
            shutil.copy2(source_path, target_path)

if __name__ == "__main__":
    single_syntax()
    # range_num = '400'
    # range_num = '1200'
    # range_num = '2000'
    # range_num = '2800'
    '''for range_num in ['400', '1200', '2000', '2800']:
        collect_test_dataset(range_num)'''