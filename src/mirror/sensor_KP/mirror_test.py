
import time
from datetime import datetime
import asyncio
from typing import Optional
# from mirror.sensor_KP.sensor import SensorReader
from mirror.amplifier.domestic_amplifier import Amplifier as DomesticAmplifier
from mirror.amplifier.imported_amplifier import Amplifier as ImportedAmplifier
from mirror.pmac_controller import PMAC_Controller, SSH_Config
import csv
from mirror.logger import setup_logger
import signal
import aiofiles
from dataclasses import dataclass
from bidict import bidict
import pathlib
from mirror.sensor_KP.one_motor_test import OneMotorTest
import pandas as pd
import inspect
from mirror.sensor_KP.one_motor_test import GLOBAL_PLOT_POOL
from mirror.sensor_KP.plot import kp
import ipaddress
from pathlib import Path

# 6个子镜对应6个pmac控制器
config0 = SSH_Config()
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
    def __init__(self, is_domestic:bool = True):
       self.logger = setup_logger()
       self.is_domestic = is_domestic  #  区分是国产的放大器还是进口的放大器，True表示国产，False表示进口
       try:
           from importlib import resources
           file = resources.files("mirror.sensor_KP").joinpath("controler2amplifier2sensor2motor.csv")
           self.df = pd.read_csv(file, sep=',', comment='#')
       except Exception as e:
           self.logger.error(f"read_csv error: {str(e)}")
           return
       pass
    
    def get_imported_amplifier_info(self):  # 进口放大器
        ttyr_list = []
        try:
            path = pathlib.Path("/dev/").iterdir()
            ttyr_list = sorted([f"{device}" for device in path if device.name.startswith("ttyr")])
            self.logger.info(f"Found {len(ttyr_list)} ttyr devices:")
            self.logger.info(*[item for item in ttyr_list])
            return ttyr_list
        except Exception as e:
            self.logger.error(f"{inspect.currentframe().f_code.co_name} 出现异常，Error: {str(e)}")
            return []
    def get_domestic_amplifier_info(self):  # 国产放大器
        dev_info = []
        start_ip = "192.168.0."  # 起始ip
        for id in range(102, 105, 1): # 全部需要19个放大器，测试时可根据需要收放
            current_ip = start_ip + str(id)
            dev_info.append({"amp_id": id-102, "ip": current_ip})
        return dev_info
    
    async def get_sensor_reader(self, amp_info):
        # loop = asyncio.get_running_loop()
        if self.is_domestic:
            sensor_reader = DomesticAmplifier(amp_info["ip"])  # 国产放大器
            await sensor_reader.connect()
            amplifier_id = amp_info["amp_id"]
            return amplifier_id, sensor_reader
        sensor_reader = ImportedAmplifier(amp_info, 3, 1.0)    # 进口放大器
        amplifier_id = int(amp_info[9:])
        return amplifier_id, sensor_reader
    
    async def one_amplifier_test(self, amp_info):
        async def _wrap_motor_test(motor_test):    # 给单个电机任务包异常捕获，异常只影响自己
            try:
                await motor_test.run_test(
                    motor_start=0, 
                    motor_stop=100, 
                    motor_step=20
                )
            except Exception as e:
                self.logger.error(f"❌ 电机{motor_test.motor_id}测试失败: {str(e)}，已安全停转")
    
        amplifier_id, sensor_reader = await self.get_sensor_reader(amp_info)
        pmac = None
        try:
            matched = self.df[(self.df['Amplifier_id'] == amplifier_id)]
            if matched.empty:
                self.logger.error(f"❌ 放大器{amplifier_id}未找到匹配记录，跳过当前放大器所有测试")
                return # 仅跳过当前放大器，不影响其他放大器
            Pmac_Controler_id = matched['Pmac_Controler_id'].values[0]
            pmac = Id2Controler[Pmac_Controler_id]
        except Exception as e:
            self.logger.error(f"❌ 放大器{amplifier_id}初始化失败: {str(e)}，跳过当前放大器")
            return # 仅跳过当前放大器

        try:
            tasks = []
            for channel_id in range(1, 9):
                if self.df[(self.df['Amplifier_id'] == amplifier_id) & (self.df['Channel_id'] == channel_id)]['Motor_id'].values[0] == -1:  # 放大器通道未连接电机
                    continue
                motor = OneMotorTest(amplifier_id, channel_id, sensor_reader, pmac, self.df)    # 测试传感器对应的电机
                task = asyncio.create_task(_wrap_motor_test(motor))
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
            self.logger.info(f"✅ 放大器{amplifier_id}所有通道测试完成")
        except Exception as e:
            self.logger.error(f"❌ 放大器测试出现异常: {str(e)}")
        finally:
            if sensor_reader:
                del sensor_reader

    async def main(self):
        async def _wrap_amp_test(amp_info):       # 给每个放大器任务也加一层异常隔离，单个放大器异常不影响其他
            try:
                await self.one_amplifier_test(amp_info)
            except Exception as e:
                self.logger.error(f"❌ 放大器{amp_info}测试异常: {str(e)}")
        
        amplifier_info_list =  self.get_domestic_amplifier_info() if self.is_domestic else self.get_imported_amplifier_info()
        if not amplifier_info_list:
            self.logger.error("❌ 没有找到任何设备，程序退出")
            return
        try:
            tasks = []
            self.logger.info(f"✅ 找到放大器设备: {[amplifier for amplifier in amplifier_info_list]}")
            for amp_info in amplifier_info_list:         # 测试设备上的所有放大器
                task = asyncio.create_task(_wrap_amp_test(amp_info))
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"程序出现异常，err_code: {str(e)}")
        finally:
           # 优雅关闭
            for controller in Id2Controler.values():
                await controller.disconnect()
    async def __aenter__(self):
        """连接所有 PMAC 控制器"""
        self.logger.info("🔌 正在连接所有 PMAC 控制器...")
        for pmac_id, pmac in Id2Controler.items():
            try:
                if not pmac.is_connected:
                    await pmac.connect()
                self.logger.info(f"✅ PMAC {pmac_id} 已连接")
            except Exception as e:
                self.logger.error(f"❌ PMAC {pmac_id}, 连接失败: {e}")
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """断开所有 PMAC 并清理资源"""
        self.logger.info("🔌 正在断开所有 PMAC 控制器...")
        for pmac_id, pmac in Id2Controler.items():
            try:
                if pmac.is_connected:
                    await pmac.disconnect()
                self.logger.info(f"✅ PMAC {pmac_id} 已断开")
            except Exception as e:
                self.logger.error(f"❌ PMAC {pmac_id} 断开失败: {e}")
        
        # 关闭绘图进程池
        self.logger.info("📊 关闭绘图进程池...")
        GLOBAL_PLOT_POOL.shutdown(wait=True)
        return False
                

if __name__ == "__main__":
    async def sensor_test():
        async with MirrorsTest(is_domestic=True) as test:
            await test.main()
    try:
        asyncio.run(sensor_test())
    except Exception as e:
        print(f"程序出现异常，正在退出..., {e}")

