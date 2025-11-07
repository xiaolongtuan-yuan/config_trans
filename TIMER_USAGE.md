# 翻译过程计时器使用说明

## 概述

本功能为配置翻译过程添加了详细的计时统计，可以统计一次翻译的总时长以及各个阶段的耗时，并对所有翻译任务计算平均值。

## 功能特性

- **阶段计时**：统计翻译过程中各个阶段的耗时
- **批量统计**：支持多次翻译的平均耗时计算
- **详细报告**：提供平均值、最小值、最大值、标准差等统计信息
- **文件保存**：自动保存统计结果到JSON文件
- **向后兼容**：不影响原有的调用方式

## 计时阶段

翻译过程包含以下计时阶段：

1. **juniper_template_insert**: Juniper模板插入（仅Juniper厂商）
2. **build_command_node**: 构建命令节点
3. **rule_mapping**: 规则映射
4. **llm_library_mapping**: LLM库映射
5. **fuzzy_mapping**: 模糊映射
6. **map_rule_freq_calculation**: 映射规则频率计算
7. **config_arranging**: 配置命令编排
8. **parameter_mapping_with_LLM**: LLM参数映射与修正
9. **print_and_save_translation**: 输出并保存翻译结果

## 使用方法

### 1. 单个翻译计时

```python
from src.timer import TranslationTimer
from src.F_device_configtrans2 import Config_Translater

# 创建计时器
timer = TranslationTimer()

# 调用翻译方法，传入计时器
result = config_translater.translation(
    json_configuration,
    source_vendor,
    target_vendor,
    timer=timer  # 传入计时器
)

# 获取计时信息
timing_info = result['timing_info']
print(f"总耗时: {timing_info['total']:.4f}s")
print(f"规则映射耗时: {timing_info['rule_mapping']:.4f}s")
```

### 2. 批量翻译计时

```python
from src.timer import BatchTimer

# 在batch_translate函数中启用计时
batch_translate(
    config_translater,
    input_dir,
    output_dir,
    real_config_dir,
    real_command_tree_dir,
    source_vendor,
    target_vendor,
    enable_timing=True  # 启用计时功能
)
```

### 3. 查看统计结果

批量翻译完成后，会自动：
- 在控制台打印统计信息
- 保存详细统计到JSON文件：`timing_statistics_{source_vendor}_to_{target_vendor}.json`

统计信息包括：
- 平均耗时
- 最小耗时
- 最大耗时
- 标准差
- 各阶段耗时占比

## 输出示例

### 控制台输出
```
=== 翻译耗时统计 ===
总翻译次数: 100
阶段                   平均耗时(s)      最小耗时(s)      最大耗时(s)      标准差(s)      
--------------------------------------------------------------------------------
config_arranging     0.1204       0.1004       0.1404       0.0159      
parameter_mapping_with_LLM 0.2902       0.2502       0.3301       0.0315      
total                1.8422       1.5526       2.1321       0.2291      
...

=== 各阶段耗时占比 ===
config_arranging         6.53%
parameter_mapping_with_LLM    15.75%
fuzzy_mapping           26.07%
...
```

### JSON文件输出
```json
{
    "total": {
        "average": 1.8422,
        "min": 1.5526,
        "max": 2.1321,
        "count": 100,
        "std": 0.2291
    },
    "rule_mapping": {
        "average": 0.3604,
        "min": 0.3006,
        "max": 0.4204,
        "count": 100,
        "std": 0.0474
    },
    ...
}
```

## 注意事项

1. **向后兼容**：如果不传入计时器参数，翻译功能完全不受影响
2. **性能开销**：计时功能开销极小，对翻译性能影响可忽略
3. **文件保存**：统计文件保存在输出目录的target_vendor子目录下
4. **多线程**：支持多线程环境下的计时统计

## 文件结构

```
src/
├── timer.py                    # 计时器类定义
├── F_device_configtrans2.py   # 修改后的翻译器（添加计时支持）
experiment/
├── exper_ours_and_rag_timing_average_100.py  # 修改后的实验文件
```

## 技术实现

- **TranslationTimer**: 单个翻译过程的计时器
- **BatchTimer**: 批量翻译的统计器
- **非侵入式设计**: 通过可选参数添加计时功能
- **自动统计**: 自动计算平均值、标准差等统计指标
