import numpy as np
import pandas as pd
import asyncio
import asyncio, time, atexit
from datetime import datetime
from multiprocessing import Process, Event
from multiprocessing.shared_memory import SharedMemory
# 映射索引

CAPACITY_SENSORS = 152
SHM_NAME = "QUEST_Mirrors_Control"

mapping = np.loadtxt("settings/Actuator_Mapping.csv", delimiter=',', skiprows=1, dtype=int)
print(f"mapping = {mapping}")
v1 = mapping[122][-2]
v2 = mapping[122][-1]
print(f"v1 = {v1}, v2 = {v2}")

def create_shm():
        # created shared memory in /dev/shm/
        shm = SharedMemory(create=True, name=SHM_NAME, size=TOTAL_BUFF_BYTES
        print(f"Created shared memory '{SHM_NAME}'")
        return shm

shm = create_shm()
buffer = np.ndarray((CAPACITY_SENSORS*2,), dtype=np.float64, buffer=shm.buf)
buffer.fill(15.0)  # 初始化共享内存数据区，避免初始全0导致的误动
data = buffer[:CAPACITY_SENSORS]       # 传感器数据视图，零拷贝

actuator_id, controller_id, axis_id, amplifer_id, channel_id = mapping.T    # 配置表拆成5个列向量
sensor_idx = amplifer_id*8 + channel_id   
print(f"sensor_idx = {sensor_idx}")

from typing import Optional

class my_A:
    def __init__(self):
        print(f"创建了一个A的对象")
        self.b = my_B()
        self.li:Optional[list] = self.b.lis[0]
        pass
    async def test(self):
        asyncio.create_task(self.b.run())
        while True:
            self.b.lis[0].append(0)
            print(f"li = {self.li}")
            print(self.li is self.b.lis[0])
            await asyncio.sleep(1)

    # @property
    # def li(self):
    #     return self.b.lis

class my_B:
    lis:Optional[list] = [[1, 1], [3, 4]]
    def __init__(self):
        # self.lis = [1, 2]
        pass
    async def run(self):
        while True:
            print(f"lis = {self.lis[0]}")
            # liss = self.lis
            await asyncio.sleep(2)



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
    a = my_A()
    try:
        asyncio.run(a.test())
    except Exception as e:
        pass
    
