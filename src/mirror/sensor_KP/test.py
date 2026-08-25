import matplotlib.pyplot as plt

# 准备数据
x = [1, 2, 3, 4, 5]
y1 = [2, 4, 6, 8, 10]
y2 = [1, 5, 4, 9, 8]

# 绘制多条折线，并自定义颜色、线条样式、标记点和标签
plt.plot(x, y1, color='blue', linestyle='--', marker='o', label='数据系列A')
plt.plot(x, y2, color='red', linestyle='-', marker='s', label='数据系列B')

# 添加图表元素
plt.title("自定义折线图示例")
plt.xlabel("X轴标签")
plt.ylabel("Y轴标签")
plt.legend()  # 显示图例
plt.grid(True)  # 显示网格线

# 显示图形
plt.show()
fit_img_path = "./fs.png"
plt.savefig(fit_img_path, dpi=300, bbox_inches='tight')
plt.close()