import numpy as np
import pandas as pd
import asyncio
# 映射索引

mapping = np.loadtxt("settings/Actuator_Mapping.csv", delimiter=',', skiprows=1, dtype=int)
print(f"mapping = {mapping}")
v1 = mapping[122][-2]
v2 = mapping[122][-1]
print(f"v1 = {v1}, v2 = {v2}")

actuator_id, controller_id, axis_id, amplifer_id, channel_id = mapping.T    # 配置表拆成5个列向量
sensor_idx = amplifer_id*8 + channel_id   
print(f"sensor_idx = {sensor_idx}")


class my_A:
    # i = 0
    def __init__(self):
        print(f"创建了一个A的对象")
        self.b = my_B()
        self.lis = [0, 1, 2]
        pass
    async def test(self):
       asyncio.create_task(self.b.run(self.lis))
       while True:
        print(f"lis = {self.lis}")
        await asyncio.sleep(1)

class my_B:
    def __init__(self):
        pass
    async def run(self, lis):
        while True:
            for i in range(len(lis)):
                lis[i] += 1
                await asyncio.sleep(1)



# DEFAULT_AMP_PORTS = [f"/dev/ttyr{i:02d}" for i in range(19)]

def load_hardware_config(filepath, col, defaults):
        try:
            data = np.loadtxt(filepath, delimiter=',', dtype=str, skiprows=1, comments='#')
        except OSError:
            return defaults.copy()
        if data.ndim == 1:              
            data = data.reshape(1, -1)  
        loaded = data[:, col].tolist() 
        print(f"1: loaded = {loaded}") 
        loaded = [s.strip() for s in loaded]  
        n = len(defaults)
        if len(loaded) < n:
            loaded.extend(defaults[len(loaded):])
        elif len(loaded) > n:
            loaded = loaded[:n]
        print(f"2: loaded = {loaded}") 
        return loaded

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

class qq(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main()
        pass
    def test(self, s:str, row, dialog, control_layout):
        ##################### 目标力 操作 ######################
        control_layout.addWidget(QLabel("s (N):"), row, 0)
        force_edit = QLineEdit("10.0")
        force_edit.setValidator(QDoubleValidator())   # 只允许数字
        control_layout.addWidget(force_edit, row, 1)

        execute_btn = QPushButton("执行")
        execute_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px;")
        control_layout.addWidget(execute_btn, row, 2)

        close_btn = QPushButton("关闭")
        control_layout.addWidget(close_btn, row, 3)

        # 连接按钮事件
        execute_btn.clicked.connect(lambda: self._test_matrix_execute(dialog, force_edit))
        close_btn.clicked.connect(dialog.close)
    def main(self):
        control_layout = QGridLayout()
        dialog = QDialog(self)
        dialog.setWindowTitle("系统响应矩阵测试 - 促动器选择")
        dialog.setModal(False)           # 非模态
        dialog.setMinimumWidth(1000)
        dialog.setMinimumHeight(600)
        main_layout = QVBoxLayout(dialog)
        main_layout.addLayout(control_layout)
        self.test("目标力", 0, dialog, control_layout)
        # self.test("增加力", 1, dialog, control_layout)


if __name__ == "__main__":
    # b = my_B()
    # a = my_A()
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # try:
    #     # loop.create_task(a.test())
    #     # loop.run_until_complete(b.run())
    #     asyncio.run(a.test())
    # except Exception as e:
    #     print(f"e = {e}")
    #     pass
    # # lis = np.zeros(12)
    # # b.run(lis)
    # # print(lis)
    # # # amplifer_ports = load_hardware_config("settings/Amplifier_Port.csv", col=1, defaults=DEFAULT_AMP_PORTS)
    import sys
    app = QApplication(sys.argv)
    win = qq()
    win.show()
    sys.exit(app.exec_())