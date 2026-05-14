import pathlib
import pandas as pd
import numpy as np

###### 获取ttryXXXX设备列表 ######
def get_ttry_devices():
     try:
        path = pathlib.Path("/dev/").iterdir()
        ttrys = sorted([device for device in path if device.name.startswith("ttyr")])
        print(f"Found {len(ttrys)} ttyr devices:")
        print(*[item.name for item in ttrys], sep=", ")
     except Exception as e:
        print(f"Error: {e}")


def test1(csv_file):
    # 示例数据：AD显示实验中可能采集的数据
    data = {
        '电压(V)': [1.1, 2.2, 3.1, 4.0, 5.2, 6.0, 7.1, 8.0],
        '电流(mA)': [10, 21, 30, 39, 52, 59, 71, 80],
        '亮度(cd/m²)': [15, 35, 50, 65, 85, 95, 120, 135],
        '响应时间(ms)': [25, 18, 15, 12, 10, 8, 7, 6]
    }
    df = pd.read_csv(csv_file)
    print("原始数据:")
    print(df)

    # 计算皮尔逊相关系数矩阵（最常用）
    print("\n📊 皮尔逊相关系数矩阵:")
    correlation = df['Steps'].corr(df['Force_Value'])
    print(f"皮尔逊相关系数: {correlation:.4f}")

    # 或者使用斯皮尔曼相关系数（对异常值更稳健）
    spearman_corr = df['Steps'].corr(df['Force_Value'], method='spearman')
    print(f"斯皮尔曼相关系数: {spearman_corr:.4f}")



if __name__ == "__main__":
    test1("data_20260510_220337.csv")