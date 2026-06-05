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
    import matplotlib
    print(matplotlib.matplotlib_fname())
    import os
    i = os.cpu_count()
    print(f"i= {i}")
    # GLOBAL_PLOT_POOL = ProcessPoolExecutor(
    #     max_workers=MAX_WORKERS,
    #     mp_context=mp_context,
    #     initializer=_worker_init
    # )

    # with GLOBAL_PLOT_POOL as executor:
        
    # with ProcessPoolExecutor(
    #     max_workers=MAX_WORKERS,
    #     mp_context=mp_context,
    #     initializer=_worker_init
    # ) as exector:

def test5():
    # 控制器返回的状态字数组，每个元素是16位整数
    status_word = np.array([0b1011, 0b1100, 0b0011])
    # 掩码：仅保留第2位（二进制0b0100=4）
    mask = 0b0100
    # 逐元素按位与，结果非0表示该位为1（电机已使能）
    enable_status = (status_word & mask) != 0
    print(enable_status) # 输出：[True, True, False]

k = np.full(10, np.nan)

def test6():
    from pymodbus.client import ModbusTcpClient
    import inspect
    print(f"inspect.signature(ModbusTcpClient.__init__): {inspect.signature(ModbusTcpClient.__init__)}")



if __name__ == "__main__":
    test6()