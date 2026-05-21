import pathlib
import pandas as pd
import numpy as np

###### 获取ttryXXXX设备列表 ######
def get_ttry_devices():
        ttyr_list = []
        try:
            path = pathlib.Path("/dev/").iterdir()
            ttyr_list = sorted([f"{device}" for device in path if device.name.startswith("ttyr")])
            print(f"Found {len(ttyr_list)} ttyr devices:")
            print(*[item for item in ttyr_list], sep=", ")
            return ttyr_list
        except Exception as e:
            print(f"Error: {e}")
            return []


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


def test2(start, stop, step):
    for i in range(start, stop, step):
        print(f"i = {i}")


def test3(file):
    import pandas as pd
    df = pd.read_csv(file,  sep=',', comment='#')  # 读取CSV文件，忽略注释行
    print(df)
    print(f"motor_id = {df[(df['dev_id'] == 0) & (df['sensor_id'] == 1)]['motor_id'].values[0]}")  # 获取dev_id=0且sensor_id=7对应的motor_id

    dev_path="/dev/ttyr01"
    n = int(dev_path[-2:])
    print(f"n = {n}")



def test4():
    from dataclasses import dataclass, asdict
    from pmac_controller import SSH_Config
    config2 = SSH_Config()
    print(config2.host) # 输出：192.168.0.201
    print(config2.port) # 输出：22（继承默认值）


if __name__ == "__main__":
    test4()