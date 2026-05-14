
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

logger = setup_logger()

motor2sensor= bidict({
    0: 0,  # motor1对应传感器的1号通道
    1: 1,  # motor2对应传感器的2号通道
    2: 2,  # motor3对应传感器的3号通道
    3: 3,  # motor4对应传感器的4号通道
    4: 4,  # motor5对应传感器的5号通道
    5: 5,  # motor6对应传感器的6号通道
    6: 6,  # motor7对应传感器的7号通道
    7: 7,  # motor8对应传感器的8号通道
})

class OneMotorTest:
    def __init__(self, motor_id: int, stop_event: asyncio.Event):
        self._stop_event = stop_event
        self.motor_id = motor_id
        self.sensor_id = motor2sensor[motor_id]  # 获取对应的传感器通道
        self.data_pairs = []                     # 存储步数和力值的列表

    async def async_input(self, prompt: str) -> str:
        """异步输入函数"""
        return await asyncio.get_running_loop().run_in_executor(None, input, prompt)

    async def save_to_csv(self):
        if self.data_pairs:
            filename = f"/data/{self.motor_id}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # 设置表头
                writer.writerow(['序号', 'Steps', 'Force_Value'])
                # 写入所有数据行
                for i, (first_data, second_data) in enumerate(self.data_pairs, 1):
                    writer.writerow([i, first_data, second_data])
            logger.info(f"\n✅ 所有数据已保存到: {filename}")
            logger.info(f"📊 共保存 {len(self.data_pairs)} 行数据")
            DataAnalyzer(filename).plot(x_col='Steps', y_col='Force_Value')
        else:
            logger.error("❌ 没有数据需要保存")
        return self.data_pairs

    def signal_handler(self, loop):
        logger.info("\n接收到关闭信号，正在退出...")

        self._stop_event.set()  # 设置停止信号
        # 取消所有任务
        for task in asyncio.all_tasks():
            task.cancel()
        loop.call_later(0.1, loop.stop)
        loop.close()
    
    async def main(self, val: Optional[float] = None):

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
                            if val is not None:
                                self.data_pairs.append((step, val))
                                logger.info(f"✅ 记录: 步数={step}, 力值={val:.3f}")
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
                    await pmac.exec_command(f"#{self.motor_id}k")
            except:
                logger.warning("⚠️ 电机停止失败")

        await self.save_to_csv(self.data_pairs)


if __name__ == "__main__":
    try:
        asyncio.run(OneMotorTest(motor_id=2).main())
    except KeyboardInterrupt:
        logger.error("程序出现异常，正在退出...")

