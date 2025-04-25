import os
from napalm import get_network_driver
from napalm.base.exceptions import MergeConfigException

# 1. 选择驱动并创建设备实例（无需真实设备，可指向模拟器或实际设备）
driver = get_network_driver('huawei_vrp')    # 社区驱动名称
device = driver(hostname='192.0.2.1', username='admin', password='pass')
device.open()                                # 建立 SSH/Telnet 会话

# 2. 遍历目录下所有 .cfg/.txt 配置文件
config_dir = '/path/to/configs'
results = {}
for fname in os.listdir(config_dir):
    if not fname.endswith(('.cfg', '.txt')):
        continue
    path = os.path.join(config_dir, fname)
    with open(path) as f:
        cfg = f.read()
    try:
        # 3. 加载候选配置（合并模式），仅做语法检查
        device.load_merge_candidate(config=cfg)
        # 4. 比较配置差异；若没有异常，则语法正确
        diff = device.compare_config()
        results[fname] = ('PASSED', diff)
    except MergeConfigException as e:
        # 5. 捕获语法/合并错误
        results[fname] = ('FAILED', str(e))

# 6. 输出结果
for file, (status, info) in results.items():
    print(f"{file}: {status}")
    if status == 'FAILED':
        print(f"  Error: {info}")
