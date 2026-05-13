
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

logger = setup_logger()

@dataclass
class SensorData:
    path:     str           # 传感器文件
    group_id: int           # 组编号，MOXA串口网口转换器
    datarate: float = 10.0  # 传感器内部采样频率
    # logger:   None        # 日志记录器

class OneMotorTest:
    def __init__(self, dev_path: str, motor_id: int, input_step):
        self.val1: Optional[float] = None
        self.val2: Optional[float] = None
        self.val3: Optional[float] = None
        self.val4: Optional[float] = None
        self.val5: Optional[float] = None
        self.val6: Optional[float] = None
        self.val7: Optional[float] = None
        self.val8: Optional[float] = None
        self.dev_path = dev_path            # 传感器设备路径
        self.motor_id = motor_id            # 电机ID
        self.input_step = input_step        # 用户输入的电机步数
        self._stop_event = asyncio.Event()

    async def async_input(self, prompt: str) -> str:
        """异步输入函数"""
        return await asyncio.get_running_loop().run_in_executor(None, input, prompt)

    async def save_to_csv(self, data_pairs):
        if data_pairs:
            filename = f"/data/data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # 设置表头
                writer.writerow(['序号', 'Steps', 'Force_Value'])
                # 写入所有数据行
                for i, (first_data, second_data) in enumerate(data_pairs, 1):
                    writer.writerow([i, first_data, second_data])
            logger.info(f"\n✅ 所有数据已保存到: {filename}")
            logger.info(f"📊 共保存 {len(data_pairs)} 行数据")
            DataAnalyzer(filename).plot(x_col='Steps', y_col='Force_Value')
        else:
            logger.error("❌ 没有数据需要保存")
        return data_pairs

    async def get_sensor_data(self):
        sensor = SensorReader(self.dev_path, 3, 1.0)
        while not self._stop_event.is_set():
            try:
                res = sensor.read_data()
                timestamp = res[1].strftime("%Y-%m-%dT%H:%M:%S.%f")
                values = res[2]
                self.val4 = values[4]  # 对应物理放大器的5号通道
                self.val5 = values[5]  # 对应物理放大器的6号通道
                # logger.info(f"[{timestamp[:-5]}]: val4={values[4]:0.3f}, val5={values[5]:0.3f}")
                async with aiofiles.open("sensor_log.txt", "a") as log_file:
                    await log_file.write(f"[{timestamp[:-5]}]: val4={values[4]:0.3f}, val5={values[5]:0.3f}\n")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Sensor reading error: {e}")

    async def safety_monitor(self):
        """安全监控任务"""
        while not self._stop_event.is_set():
            await asyncio.sleep(0.1)
            if self.val4 is not None and (self.val4 > 80.0 or self.val4 < -80.0):
                logger.warning("⚠️  val4 out of bounds! Stopping system.")
                self._stop_event.set()  # 设置停止信号
                break

    def signal_handler(self, loop):
        logger.info("\n接收到关闭信号，正在退出...")

        self._stop_event.set()  # 设置停止信号
        # 取消所有任务
        for task in asyncio.all_tasks():
            task.cancel()
        loop.stop()

    async def main(self):
        data_pairs = []
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
                    await pmac.exec_command(f"#{self.motor_id}J/")

                    # 启动所有任务
                    sensor_task = asyncio.create_task(self.get_sensor_data())
                    safety_task = asyncio.create_task(self.safety_monitor())

                    while not self._stop_event.is_set():
                        step = await self.async_input("请输入步数: ")
                        if step.lower() == 'exit':
                            break
                        try:
                            await pmac.exec_command(f"#{self.motor_id}J={step}")
                            await asyncio.sleep(10)  # 等待数据稳定
                            if self._stop_event.is_set():
                                logger.info("🛑 安全监控触发，提前终止等待")
                                break
                            if self.val4 is not None:
                                data_pairs.append((step, self.val4))
                                logger.info(f"✅ 记录: 步数={step}, 力值={self.val4:.3f}")
                            else:
                                logger.warning("⚠️ 传感器数据为空")
                        except Exception as e:
                            logger.error(f"Error executing command: {e}")
                            break
                except Exception as e:
                    logger.error(f"Error: {e}")
        except Exception as e:
            logger.error(f"💥 系统错误: {e}")
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
                    await pmac.exec_command(f"#{motor_id}k")
            except:
                logger.warning("⚠️ 电机停止失败")

        await self.save_to_csv(data_pairs)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.error("程序出现异常，正在退出...")
        pass

