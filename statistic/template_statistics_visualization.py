import json
import numpy as np
import matplotlib.pyplot as plt

# 设置全局字体为 "New Times Roman"
plt.rcParams["font.family"] = "Times New Roman"
vendors = ["Cisco", "Huawei", "Juniper"]

# 创建一张图，其中包含三个并排的子图，图像大小可以根据需要调整
fig, axes = plt.subplots(1, len(vendors), figsize=(36, 8))

for i, vendor in enumerate(vendors):
    # 读取 JSON 文件中的数据
    with open(f"./statistic_res/{vendor}_template_used_statistic.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 取前 top_n 项数据进行绘图
    top_n = 500 if vendor == "Cisco" else 1000 if vendor == "Juniper" else 500
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    x_labels, y_values = zip(*sorted_items)
    x_positions = np.arange(len(x_labels))

    # 计算累计使用次数占总数的比例
    total_usage = sum(y_values)
    cumulative_usage = np.cumsum(y_values)
    cumulative_percentage = cumulative_usage / total_usage

    # 找到第一个累计百分比达到或超过80%的索引
    threshold_index = np.argmax(cumulative_percentage >= 0.8)
    # 计算前面的轴数量占总轴数量的百分比
    threshold_ratio = (threshold_index + 1) / len(x_labels) * 100
    print(f"达到80%累计百分比时，前面的轴数量占总轴数量的 {threshold_ratio:.2f}%")

    # 将原始使用次数转换为占总数的比例
    y_proportions = np.array(y_values) / total_usage

    # 获取当前子图的坐标轴
    ax = axes[i]
    ax.bar(x_positions, y_proportions, color='green', width=1.0)

    # 绘制竖虚线（加 1 是为了让虚线更接近柱状图对应位置，根据具体数据适当调整）
    ax.axvline(x=threshold_index + 1, color='red', linestyle='--', linewidth=2)

    # 获取 y 轴最大值，并设置横向偏移，使文本出现在虚线右侧
    y_max = max(y_proportions)
    print(y_max)
    x_offset = 6  # 根据实际情况调整偏移量
    ax.text(threshold_index + x_offset, y_max * 0.95, f'{threshold_ratio:.2f}%', color='red', fontsize=30,
            horizontalalignment='left', verticalalignment='top')

    # 设置当前子图的标签、标题及其他属性
    ax.set_xlabel(f'{vendor} Commands', fontsize=30)
    ax.set_ylabel('Usage Frequency', fontsize=30)
    ax.set_xticks([])
    # 设置 y 轴刻度的字体大小
    ax.tick_params(axis='y', labelsize=20)

# 调整整体子图布局，并保存最终的合并图形
plt.tight_layout()
plt.savefig("./statistic_res/combined_template_usage_count_bar_charts.pdf")
plt.show()