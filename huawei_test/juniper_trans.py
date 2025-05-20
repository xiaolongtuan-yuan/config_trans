import re


def view_to_command(view_config: str) -> str:
    """
    将Junos视图级配置转换为命令级配置

    参数:
        view_config: 视图级配置字符串
        indent_size: 缩进空格数，默认为4（Junos标准）

    返回:
        命令级配置字符串，每条命令用换行符分隔
    """
    commands = []
    current_path = []
    stack = []  # 用于跟踪层级关系

    # 将所有行合并为一行，并去除多余空格
    single_line = ' '.join(view_config.strip().split())

    # 根级别配置及其对应的命令级前缀映射
    root_configs = {
        "protocols": "protocols",
        "system": "system",
        "interfaces": "interfaces",
        "policy-options": "policy-options",
        "firewall": "firewall",
        "security": "security",
        "routing-options": "routing-options",
    }

    # 子配置及其对应的父级根配置映射
    sub_configs = {
        "bgp": "protocols",
        "ospf": "protocols",
        "isis": "protocols",
        "rip": "protocols",
        "static": "protocols",
        "pim": "protocols",
        "mpls": "protocols",
        "host-name": "system",
        "domain-name": "system",
        "name-server": "system",
        "time-zone": "system",
        "location": "system",
        "contact": "system",
        "services": "system",
        "login": "system",
        "ntp": "system",
        "snmp": "system",
        "radius": "system authentication-order",
        "syslog": "system",
    }

    # 跟踪已存在于路径中的根配置
    active_root_configs = set()

    # 修改正则表达式，仅把大括号作为分隔符
    pattern = re.compile(r'([^{}]+?)([{}]|$)')
    matches = pattern.finditer(single_line)

    for match in matches:
        config = match.group(1).strip()
        delimiter = match.group(2)

        if not config:
            continue

        # 处理配置块开始
        if delimiter == '{':
            # 处理根级别配置
            if config in root_configs:
                current_path.append(root_configs[config])
            # 处理需要父级根配置的子配置
            elif config in sub_configs:
                parent_root = sub_configs[config]
                if parent_root not in current_path:
                    current_path.append(f"{parent_root} {config}")
                else:
                    current_path.append(config)
            # 普通配置块
            else:
                current_path.append(config)
            stack.append(len(current_path))  # 记录当前层级深度

        # 处理配置块结束
        elif delimiter == '}':
            # 处理配置项，将配置按分号分割
            config_items = config.split(';')
            for item in config_items:
                item = item.strip()
                if not item:
                    continue
                # 分离关键字和值
                parts = item.split()
                if parts:
                    keyword = parts[0]
                    value = ' '.join(parts[1:]) if len(parts) > 1 else ""

                    # 检查关键字是否是子配置，如果是则补全父视图
                    if keyword in sub_configs:
                        parent_root = sub_configs[keyword]
                        # 如果父级根配置不在路径中，添加它
                        if parent_root not in active_root_configs:
                            current_path.append(parent_root)
                            active_root_configs.add(parent_root)
                        # 添加子配置到路径
                        if keyword not in current_path:
                            current_path.append(keyword)

                    # 构建完整命令，移除路径中最后一个与keyword相同的部分
                    path_str = ' '.join(current_path) if current_path else ''
                    if current_path and current_path[-1] == keyword:
                        path_str = ' '.join(current_path[:-1]) if current_path[:-1] else ''
                    cmd = f"set {path_str} {keyword} {value}".strip()
                    commands.append(cmd)

            if stack:
                # 回退到上一层级
                prev_level = stack.pop()
                while len(current_path) >= prev_level:
                    current_path.pop()

        # 处理配置项
        else:
            # 将配置按分号分割
            config_items = config.split(';')
            for item in config_items:
                item = item.strip()
                if not item:
                    continue
                # 分离关键字和值
                parts = item.split()
                if parts:
                    keyword = parts[0]
                    value = ' '.join(parts[1:]) if len(parts) > 1 else ""

                    # 检查关键字是否是子配置，如果是则补全父视图
                    if keyword in sub_configs:
                        parent_root = sub_configs[keyword]
                        # 如果父级根配置不在路径中，添加它
                        if parent_root not in active_root_configs:
                            current_path.append(parent_root)
                            active_root_configs.add(parent_root)
                        # 添加子配置到路径
                        if keyword not in current_path:
                            current_path.append(keyword)

                    # 构建完整命令，移除路径中最后一个与keyword相同的部分
                    path_str = ' '.join(current_path) if current_path else ''
                    if current_path and current_path[-1] == keyword:
                        path_str = ' '.join(current_path[:-1]) if current_path[:-1] else ''
                    cmd = f"set {path_str} {keyword} {value}".strip() if path_str else f"set {keyword} {value}".strip()
                    commands.append(cmd)

    return '\n'.join(commands)


# 示例用法
if __name__ == "__main__":
    view_config = """
 lacp {
                active;
                periodic fast;
            }               
    """
    print(view_to_command(view_config))

