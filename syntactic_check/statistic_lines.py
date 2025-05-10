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

def statistic_config_lines(range_num):
    summary_path = f'syntactic_check/config_data_{range_num}/error_info/config_summary.json'
    summary_info = load_json_file(summary_path)
    all_config = [config_name.replace(".txt", "") for config_name in summary_info['all_config']['config']]
    test_config = [config_name.replace(".txt", "") for config_name in summary_info['test_config']['config']]
    # 统计配置文件行数
    config_lines = {}
    for vendor in ['Cisco', 'HUAWEI','Juniper']:
        # 所有的配置文件行数
        all_config_line = {}
        all_lines_count = 0
        for config_name in all_config:
            config_file_path = f'syntactic_check/config_data_{range_num}/{vendor}_config/{vendor}_{config_name}/configs/{config_name}.cfg'
            # 统计行数
            with open(config_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                non_blank_lines = [line for line in lines if line.strip()]
                all_config_line[config_name] = len(non_blank_lines)
                all_lines_count += len(non_blank_lines)
        # 测试的配置文件行数
        test_config_line = {}
        test_lines_count = 0
        for config_name in test_config:
            config_file_path = f'syntactic_check/config_data_{range_num}/{vendor}_config/{vendor}_{config_name}/configs/{config_name}.cfg'
            # 统计行数
            with open(config_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                non_blank_lines = [line for line in lines if line.strip()]
                test_config_line[config_name] = len(non_blank_lines)
                test_lines_count += len(non_blank_lines)
        config_lines[vendor] = {'average_all_lines': all_lines_count/len(all_config), 
                                'average_test_lines': test_lines_count/len(test_config), 
                                'all_config_line': all_config_line, 
                                'test_config_line': test_config_line}
    # 保存配置文件行数
    save_json_file(config_lines, f'syntactic_check/config_data_{range_num}/error_info/config_lines.json')
    return config_lines


if __name__ == "__main__":

    range_num = ['400', '1200', '2000','2800']
    all_config_lines = {j:0 for j in ['Cisco', 'HUAWEI','Juniper']}
    for i in range_num:
        config_lines = statistic_config_lines(i)
        for j in ['Cisco', 'HUAWEI','Juniper']:
            print(f"{j}的平均行数为：{config_lines[j]['average_all_lines']}")
            all_config_lines[j] += sum(list(config_lines[j]['all_config_line'].values()))
    
    for vendor in all_config_lines.keys():
        all_config_lines[vendor] = all_config_lines[vendor] / 1693
    print(all_config_lines)


