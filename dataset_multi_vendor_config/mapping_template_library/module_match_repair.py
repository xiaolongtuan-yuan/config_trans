import json

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

def k_v_exchange(data):
    new_data = {}
    for k, v in data.items():
        if v not in new_data.keys():
            new_data[v] = k
    return new_data

def main():
    # Load the JSON file
    for vendor in ['Cisco', 'HUAWEI']:
        input_file_path = f'./dataset_multi_vendor_config/mapping_template_library/scale400/Juniper_{vendor}_module_match.json'
        output_file_path = f'./dataset_multi_vendor_config/mapping_template_library/scale400/{vendor}_Juniper_module_match.json'
        data = load_json_file(input_file_path)  
        new_data = k_v_exchange(data)
        print(f"new_data: {new_data}")
        save_json_file(new_data, output_file_path)
        print(f"JSON file saved to {output_file_path}")

if __name__ == "__main__":
    main()
        