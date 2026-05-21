
import time
from datetime import datetime
import asyncio
from typing import Optional
from sensor import SensorReader
from pmac_controller import PMAC_Controller, SSH_Config
import csv
from plot_show import DataAnalyzer
from logger import setup_logger
import signal
import aiofiles
from dataclasses import dataclass
from bidict import bidict
import pathlib
from one_motor_test import OneMotorTest
import pandas as pd
import inspect

# 6个子镜对应6个pmac控制器
config0 = SSH_Config(host = "192.168.0.200")
pmac_controler0 = PMAC_Controller(config0)

config1 = SSH_Config(host = "192.168.0.201")
pmac_controler1 = PMAC_Controller(config1)

config2 = SSH_Config(host = "192.168.0.202")
pmac_controler2 = PMAC_Controller(config2)

config3 = SSH_Config(host = "192.168.0.203")
pmac_controler3 = PMAC_Controller(config3)

config4 = SSH_Config(host = "192.168.0.204")
pmac_controler4 = PMAC_Controller(config4)

config5 = SSH_Config(host = "192.168.0.205")
pmac_controler5 = PMAC_Controller(config5)


Id2Controler = {
    0: pmac_controler0,
    1: pmac_controler1,
    2: pmac_controler2,
    3: pmac_controler3,
    4: pmac_controler4,
    5: pmac_controler5
}

class MirrorsTest:
    def __init__(self):
       self.logger = setup_logger()
       pass
    
    def get_ttry_devices(self):
        ttyr_list = []
        try:
            path = pathlib.Path("/dev/").iterdir()
            ttyr_list = sorted([f"{device}" for device in path if device.name.startswith("ttyr")])
            self.logger(f"Found {len(ttyr_list)} ttyr devices:")
            self.logger(*[item for item in ttyr_list], sep=", ")
            return ttyr_list
        except Exception as e:
            self.logger(f"{inspect.currentframe().f_code.co_name} 出现异常，Error: {str(e)}")
            return []
    
    async def one_amplifier_test(self, amplifier):
        sensor = SensorReader(path=amplifier, group_id=3, datarate=1.0)   # 一个放大器上的8个通道共用一个读取器
        amplifier_id = int(amplifier[4:])
        pmac_controler = None

        try:
            df = pd.read("controler2amplifier2sensor2motor.csv", sep=',', comment='#')
            matched = df[(df['Amplifier_id'] == amplifier_id)]
            if matched.empty:
                self.logger.error(f"❌ 放大器{amplifier_id}未找到匹配记录，跳过当前放大器所有测试")
                return # 仅跳过当前放大器，不影响其他放大器
            Pmac_Controler_id = matched['Pmac_Controler_id'].values[0]
            pmac_controler = Id2Controler[Pmac_Controler_id]
        except Exception as e:
            self.logger.error(f"❌ 放大器{amplifier_id}初始化失败: {str(e)}，跳过当前放大器")
            return # 仅跳过当前放大器

        try:
            async with pmac_controler as pmac:
                tasks = []
                if not pmac.is_connected:
                    await pmac.connect()
                for channel_id in range(1, 3):
                    motor = OneMotorTest(amplifier_id, channel_id, sensor, pmac)    # 测试传感器对应的电机
                    
                    async def _wrap_motor_test(motor_test):                         # 给单个电机任务包异常捕获，异常只影响自己
                        try:
                            await motor_test.run_test(
                                motor_start=0, 
                                motor_stop=100, 
                                motor_step=20
                            )
                        except Exception as e:
                            self.logger.error(f"❌ 电机{motor_test.motor_id}测试失败: {str(e)}，已安全停转")

                    task = asyncio.create_task(_wrap_motor_test(motor))
                    tasks.append(task)
                await asyncio.gather(*tasks, return_exceptions=True)
                self.logger.info(f"✅ 放大器{amplifier_id}所有通道测试完成")
        except Exception as e:
            self.logger.error(f"❌ 放大器测试出现异常: {str(e)}")

    async def main(self):
        amplifier_list = self.get_ttry_devices()
        if not amplifier_list:
            self.logger.error("❌ 没有找到任何ttyr设备，程序退出")
            return
        try:
            tasks = []
            self.logger.info(f"✅ 找到ttyr设备: {[amplifier for amplifier in amplifier_list]}")
            for amplifier in amplifier_list:         # 测试设备上的所有放大器
                
                async def _wrap_amp_test(amp):       # 给每个放大器任务也加一层异常隔离，单个放大器异常不影响其他
                    try:
                        await self.one_amplifier_test(amp)
                    except Exception as e:
                        self.logger.error(f"❌ 放大器{amp}测试异常: {str(e)}")
                
                task = asyncio.create_task(_wrap_amp_test(amplifier))
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"程序出现异常，err_code: {str(e)}")
        finally:
            import os
            os._exit(0)
                

if __name__ == "__main__":
    try:
        asyncio.run(MirrorsTest().main())
    except Exception as e:
        print(f"程序出现异常，正在退出..., {e}")
        pass

