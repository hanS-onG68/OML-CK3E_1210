
import time
from datetime import datetime
import asyncio
from typing import Optional
from sensor import SensorReader
from pmac_controller import PMAC_Controller
import csv
from plot_show import DataAnalyzer
from logger import setup_logger
import signal
import aiofiles
from dataclasses import dataclass
from bidict import bidict
import pathlib
from one_motor_test import OneMotorTest

logger = setup_logger()


class OneDevTest:
    def __init__(self):
       pass
    
    def get_ttry_devices(self):
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
    
    async def one_amplifier_test(self, dev):
        tasks = []
        sensor = SensorReader(path=dev, group_id=3, datarate=1.0)   # 一个放大器上的8个通道共用一个读取器
        dev_id=int(dev[-2:])
        for channel_id in range(1, 9):
            motor = OneMotorTest(dev_id, channel_id, sensor)    # 测试传感器对应的电机
            task = asyncio.create_task(motor.run_test(motor_start=0, motor_stop=100, motor_step=10))
            await asyncio.sleep(0.1)  # 等待任务创建完成
            tasks.append(task)
        return tasks

    async def dev_test(self):
        dev_list = self.get_ttry_devices()
        if not dev_list:
            logger.error("❌ 没有找到任何ttyr设备，程序退出")
        else:
            logger.info(f"✅ 找到ttyr设备: {[dev for dev in dev_list]}")
            for dev in dev_list:         # 测试设备上的所有放大器
                await self.one_amplifier_test(dev)
                

        


if __name__ == "__main__":
    try:
        asyncio.run(OneDevTest().dev_test())
    except Exception as e:
        logger.error(f"程序出现异常，正在退出..., {e}")
        pass

