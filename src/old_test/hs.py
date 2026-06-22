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
    # from pymodbus.client import ModbusTcpClient
    # import inspect
    # print(f"inspect.signature(ModbusTcpClient.__init__): {inspect.signature(ModbusTcpClient.__init__)}")

    import pyqtgraph as pg
    import numpy as np
    # 直接弹出窗口绘制正弦曲线
    pg.plot(np.sin(np.linspace(0, 10, 1000)), title="调试用波形图")

    p = pg.GraphicsLayoutWidget()
    p.ci = [1, 2]
    print(f"pos = {p.ci}")


from PySide2.QtWidgets import *
import sys
class test(QWidget):
    def __init__(self):
        super().__init__()
        self.set_GUI()

    def set_GUI(self):
        self.checkbox()
        self.pushbutton()

    def checkbox(self):
        self.checkbox1 = QCheckBox(self)
        self.checkbox1.setText("选项1")
        self.checkbox1.setChecked(True)  # 默认选中
        self.checkbox1.stateChanged.connect(lambda state: print(f"当前状态 = {state}"))

        self.checkbox2 = QCheckBox(self)
        self.checkbox2.setText("选项2")
        self.checkbox2.setChecked(True)  # 默认选中
        self.checkbox2.stateChanged.connect(lambda state: print(f"当前状态 = {state}"))

        self.layout1 = QGridLayout(self)
        self.layout1.addWidget(self.checkbox1, 0, 0)
        self.layout1.addWidget(self.checkbox2, 1, 0)

        self.groupbox = QGroupBox("test", self)
        self.groupbox.setLayout(self.layout1)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.groupbox)
        self.setLayout(self.main_layout)
        # 可以顺便给窗口设个初始大小，体验更好
        self.resize(500, 300)
    def pushbutton(self):
        self.button = QPushButton("按钮", self)
        self.button.setCheckable(True)

        self.layout1.addWidget(self.button, 2, 0)


import sys
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import *

class Demo(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # 1. 创建一个工具栏
        toolbar = QToolBar()
        # 2. 创建QToolButton并设置
        btn = QToolButton()
        btn.setIcon(QIcon('icon.png'))  # 替换为你的图标路径
        btn.setText("保存")
        # 图标在上，文字在下
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setToolTip("保存当前文件")
        # 启用自动提升
        btn.setAutoRaise(True)
        btn.clicked.connect(lambda: print("保存功能被触发"))

        # 3. 为按钮添加一个下拉菜单
        self.menu = QMenu()
        self.menu.addAction("另存为...")
        self.menu.addAction("导出为PDF")
        btn.setMenu(self.menu)
        # 设置为点击小箭头才弹出菜单
        btn.setPopupMode(QToolButton.MenuButtonPopup)

        # 将按钮添加到工具栏
        toolbar.addWidget(btn)

        # 布局
        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        self.setLayout(layout)
        self.setWindowTitle('QToolButton 示例')
        self.resize(500, 300)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Demo()
    win.show()
    sys.exit(app.exec_())