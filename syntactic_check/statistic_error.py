import json
import os

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

def statistic_error_num_info(info_error_path):
    # 统计错误信息
    error_info = load_json_file(info_error_path)
    error_num = len(error_info)
    # 统计错误信息数量
    error_info_num = {}
    for filename, error in error_info.items():
        if 'line' in error.keys():
            num = len(error['line'])
            if num not in error_info_num.keys():
                error_info_num[num] = [1,[filename]]
            else:
                error_info_num[num][0] += 1
                error_info_num[num][1].append(filename)
    return error_num, error_info_num

def statistic_test_config(vendors = ['Cisco', 'Juniper'], range_num='400'):
    config_summary = {}
    file_name_path = f'syntactic_check/config_data_{range_num}/Cisco_config/'
    all_config = [filename.replace("Cisco_", "")+'.txt' for filename in os.listdir(file_name_path)]
    config_summary['all_config'] = {'num':len(all_config), 'config': all_config}
    error_config = []
    # 统计错误信息
    for vendor in vendors:
        error_info_path = f'syntactic_check/config_data_{range_num}/error_info/{vendor}_error_syntax.json'
        error_info = load_json_file(error_info_path)
        error_config.append(list(error_info.keys()))  
    Cisco_test_config = set(all_config)-set(error_config[0])
    Juniper_test_config = set(all_config)-set(error_config[1])
    test_file = list(Cisco_test_config & Juniper_test_config)
    print("测试文件：", len(test_file), test_file)
    config_summary['test_config'] = {'num': len(test_file), 'config': test_file}
    save_json_file(config_summary, f'syntactic_check/config_data_{range_num}/error_info/config_summary.json')
    return config_summary

if __name__ == "__main__":
    vendors = ['Cisco', 'Juniper']
    range_num='2800'
    summary_error_info = {}
    for vendor in vendors:
        # 统计错误信息
        error_info_path = f'syntactic_check/config_data_{range_num}/error_info/{vendor}_error_syntax.json'
        error_num, error_info_num = statistic_error_num_info(error_info_path)
        summary_error_info[vendor] = {'error_num': error_num, 'error_info_num': error_info_num}
    save_json_file(summary_error_info, f'syntactic_check/config_data_{range_num}/error_info/summary_error_info.json')
    print("统计错误信息完成！" )#, summary_error_info)
    test_file = statistic_test_config(vendors, range_num)