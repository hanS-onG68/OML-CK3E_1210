
import time
from datetime import datetime
import asyncio
from typing import Optional, List
from sensor import SensorReader
from pmac_controller import PMAC_Controller
import csv
from plot_show import DataAnalyzer
from logger import setup_logger
import signal
import aiofiles
from dataclasses import dataclass
from bidict import bidict
import pandas as pd

# self.logger = setup_logger()

# motor2sensor= bidict({
#     0: 0,  # motor1对应传感器的1号通道
#     1: 1,  # motor2对应传感器的2号通道
#     2: 2,  # motor3对应传感器的3号通道
#     3: 3,  # motor4对应传感器的4号通道
#     4: 4,  # motor5对应传感器的5号通道
#     5: 5,  # motor6对应传感器的6号通道
#     6: 6,  # motor7对应传感器的7号通道
#     7: 7,  # motor8对应传感器的8号通道
# })

class OneMotorTest:
    def __init__(self, dev_id: int, channel_id: int, sensor: SensorReader):
        self._stop_event = asyncio.Event()
        try:
            self.df = pd.read_csv("dev2sensor2motor.csv", sep=',', comment='#')  # 读取CSV文件，忽略注释行
            matched = self.df[(self.df['sensor_id'] == self.sensor_id) & (self.df['dev_id'] == dev_id)]
            if matched.empty:
                raise ValueError(f"未找到匹配的设备ID {dev_id} 和传感器通道 {channel_id} 的记录")
        except Exception as e:
            self.logger.critical(f"映射表加载失败: {str(e)}")
            raise SystemExit(1)
        
        self.sensor_id = channel_id                                          # channel_id 从下标1开始，与物理通道标值对应
        self.motor_id = self.df[(self.df['sensor_id'] == self.sensor_id) & (self.df['dev_id'] == dev_id)]['motor_id'].values[0]
        self.data_pairs = []                      # 存储步数和力值的列表
        self.sensor = sensor
        # self.chan0_val: Optional[float] = None    # 对应物理放大器的1号通道
        # self.chan1_val: Optional[float] = None    # 对应物理放大器的2号通道
        # self.chan2_val: Optional[float] = None    # 对应物理放大器的3号通道
        # self.chan3_val: Optional[float] = None    # 对应物理放大器的4号通道
        # self.chan4_val: Optional[float] = None    # 对应物理放大器的5号通道
        # self.chan5_val: Optional[float] = None    # 对应物理放大器的6号通道
        # self.chan6_val: Optional[float] = None    # 对应物理放大器的7号通道
        # self.chan7_val: Optional[float] = None    # 对应物理放大器的8号通道
        self.channel_vals: List[Optional[float]] = [None] * 8  # 用列表存8个通道值，替代冗余变量
        self.val:Optional[float] = None                        # 当前测试电机对应的传感器通道的值
        self.logger = setup_logger()


    async def save_to_csv(self):
        if self.data_pairs:
            filename = f"data/motor{self.motor_id}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            async with aiofiles.open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # 设置表头
                await file.write('序号,Steps,Force_Value\n')
                # 写入所有数据行
                for i, (step, force) in enumerate(self.data_pairs, 1):
                    await file.write(f"{i},{step},{force}\n")
            self.logger.info(f"\n✅ 所有数据已保存到: {filename}")
            self.logger.info(f"📊 共保存 {len(self.data_pairs)} 行数据")
            # DataAnalyzer(filename).plot(y_col='Steps', x_col='Force_Value')
            # 绘图逻辑如果是同步的，放在线程池里跑避免阻塞
            # loop = asyncio.get_running_loop()
            await asyncio.run_in_executor(None, DataAnalyzer(filename).plot, 'Steps', 'Force_Value')
        else:
            self.logger.error("❌ 没有数据需要保存")
        return self.data_pairs

    async def get_sensor_data(self):
        def format_val(val: Optional[float]) -> str:
            return f"{val:.3f}" if val is not None else "None"
        
        # loop = asyncio.get_running_loop()
        # sensor = SensorReader(self.dev_path, 3, 1.0)
        while not self._stop_event.is_set():
            try:
                # res = self.sensor.read_data()
                # 同步读传感器放到线程池执行，避免阻塞事件循环
                res = await asyncio.run_in_executor(None, self.sensor.read_data)
                timestamp = res[1].strftime("%Y-%m-%dT%H:%M:%S.%f")
                sensor_values = res[2]

                # self.chan0_val = sensor_values[0]
                # self.chan1_val = sensor_values[1]
                # self.chan2_val = sensor_values[2]
                # self.chan3_val = sensor_values[3]
                # self.chan4_val = sensor_values[4]
                # self.chan5_val = sensor_values[5]
                # self.chan6_val = sensor_values[6]
                # self.chan7_val = sensor_values[7]
                self.channel_vals = sensor_values  # 更新通道值列表

                self.val = sensor_values[self.sensor_id - 1]  # 获取对应电机的传感器通道值

                print(f"[{timestamp[:-5]}]: chan{self.sensor_id}_val={self.val}\n")
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Sensor reading error: {e}")

    async def safety_monitor(self):
        """安全监控任务"""
        while not self._stop_event.is_set():
            await asyncio.sleep(0.1)
            if self.val is not None and (self.val > 80.0 or self.val < -80.0):
                self.logger.warning("⚠️  self.val out of bounds! Stopping system.")
                self._stop_event.set()  # 设置停止信号
                break
    
    def signal_handler(self, loop):
        self.logger.info("\n接收到关闭信号，正在退出...")
        self._stop_event.set()  # 设置停止信号
        # 取消所有任务
        for task in asyncio.all_tasks():
            task.cancel()
        loop.call_later(0.1, loop.stop)
        loop.close()
    
    async def main(self, motor_start, motor_stop, motor_step):
        sensor_task = None
        safety_task = None

        # 设置信号处理
        loop = asyncio.get_running_loop()
        for sig in [signal.SIGINT, signal.SIGTERM]:  # Ctrl+C 和 kill 信号
            loop.add_signal_handler(sig, self.signal_handler, loop)

        try:
            async with PMAC_Controller() as pmac:
                if not pmac.is_connected:
                    await pmac.connect()
                try:
                    await pmac.exec_command(f"#{self.motor_id}J/")  # 使能电机

                    sensor_task = asyncio.create_task(self.get_sensor_data())
                    safety_task = asyncio.create_task(self.safety_monitor())
                    for step in range(motor_start, motor_stop, motor_step):
                        if not self._stop_event.is_set():
                            # step = input("请输入步数: ")
                            # if step.lower() == 'exit':
                            #     break
                            try:
                                await pmac.exec_command(f"#{self.motor_id}J={step}")
                                await asyncio.sleep(10)  # 等待数据稳定
                                if self._stop_event.is_set():
                                    self.logger.info("🛑 安全监控触发，提前终止等待")
                                    break
                                if self.val is not None:
                                    self.data_pairs.append((step, self.val))
                                    self.logger.info(f"✅ 记录: 步数={step}, 力值={self.val:.3f}")
                                else:
                                    self.logger.warning("⚠️ 传感器数据为空")
                            except Exception as e:
                                self.logger.error(f"Error executing command: {e}")
                                break
                except Exception as e:
                    self.logger.error(f"Error: {e}")
        except Exception as e:
            self.logger.error(f"💥 系统错误: {e}")
        finally:
            # 清理
            self._stop_event.set()

            # 安全停止任务
            tasks = []
            if sensor_task: tasks.append(sensor_task)
            if safety_task: tasks.append(safety_task)
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # 停止电机
            try:
                async with PMAC_Controller() as pmac:
                    await pmac.connect()
                    await pmac.exec_command(f"#{self.motor_id}k")
                    self.logger.info(f"电机_{self.motor_id} 已经完成去使能!")
            except:
                self.logger.warning("⚠️ 电机停止失败")

        await self.save_to_csv()


if __name__ == "__main__":
    dev_path = "/dev/ttyr01"
    sensor = SensorReader(path=dev_path, group_id=3, datarate=1.0)
    try:
        asyncio.run(OneMotorTest(dev_id=int(dev_path[-2:]), channel_id=8, sensor=sensor).main(motor_start=0, motor_stop=40000, motor_step=2500))  # 测试范围和步长
    except KeyboardInterrupt:
        print("[ERROR] 程序出现异常，正在退出...")

