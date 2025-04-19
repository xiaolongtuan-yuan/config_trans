import json

# load JSON fie and load data
def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data

vendors = ['Cisco', 'HUAWEI', 'Juniper']
for vendor1 in vendors:
    for vendor2 in vendors:
        if vendor1 == vendor2:
            continue
        file_name = '{}_{}_map_rule_freq.json'.format(vendor1, vendor2)
        data = load_json_file(file_name)
        total_frequency = 0
        Threshold_value = 0.70
        rule_count = 0
        for key, value in data.items():
            rule_count += 1
            total_frequency += value
            if total_frequency > Threshold_value:
                break
        print('The rule count of {}_{} is {}, and the total frequency is {}'.format(vendor1, vendor2, rule_count, total_frequency))
