import json
import pathlib
from pathlib import Path

# load JSON fie and load data
def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data


vendors = ["Cisco", "HUAWEI", "Juniper"]
project_root = Path(__file__).parent.parent
for vendor in vendors:
    command_node_path = f'scale388en/{vendor}_388.json'
    dic_data = load_json_file(command_node_path)
    commands = dic_data.keys()
    # print(commands)
    output_path = pathlib.Path(f"commands/{vendor}_commands.txt")
    with output_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(commands))  # 用换行符连接后一次性写入