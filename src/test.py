import time
from datetime import datetime
import asyncio
from typing import Optional
from sensor import SensorReader
from pmac_controller import PMAC_Controller
import csv
from plt_show import plot_trend_matplotlib
import signal

import curses

#######################################################
class CursesUI:
    """基于curses的终端UI"""
    def __init__(self):
        self.stdscr = None
        self.sensor_win = None
        self.input_win = None
        self.sensor_line = 1  # 传感器数据显示起始行
    
    async def init_ui(self):
        """初始化curses界面"""
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        
        # 创建分区
        height, width = self.stdscr.getmaxyx()
        self.sensor_win = curses.newwin(height-3, width, 0, 0)
        self.input_win = curses.newwin(3, width, height-3, 0)
        
        self.sensor_win.scrollok(True)
        self.sensor_win.idlok(True)
        
        # 绘制边框和标题
        self.sensor_win.border()
        self.input_win.border()
        self.sensor_win.addstr(0, 2, " 传感器数据 ")
        self.input_win.addstr(0, 2, " 输入区域 ")
        
        # 初始化传感器数据显示区域
        self.sensor_win.addstr(1, 1, "等待传感器数据...")
        
        self.sensor_win.refresh()
        self.input_win.refresh()
    
    async def display_sensor_data(self, timestamp, val4, val5):
        """在传感器窗口显示数据"""
        if self.sensor_win:
            # 如果数据行太多，清屏重新开始
            if self.sensor_line >= self.sensor_win.getmaxyx()[0] - 2:
                self.sensor_win.clear()
                self.sensor_win.border()
                self.sensor_win.addstr(0, 2, " 传感器数据 ")
                self.sensor_line = 1
            
            # 显示传感器数据
            self.sensor_win.addstr(self.sensor_line, 1, f"[{timestamp}]: val4={val4:0.3f}, val5={val5:0.3f}")
            self.sensor_line += 1
            self.sensor_win.refresh()
    
    async def display_message(self, message):
        """在传感器窗口显示普通消息"""
        if self.sensor_win:
            if self.sensor_line >= self.sensor_win.getmaxyx()[0] - 2:
                self.sensor_win.clear()
                self.sensor_win.border()
                self.sensor_win.addstr(0, 2, " 传感器数据 ")
                self.sensor_line = 1
            
            self.sensor_win.addstr(self.sensor_line, 1, message)
            self.sensor_line += 1
            self.sensor_win.refresh()
    
    async def get_input(self, prompt):
        """在输入窗口获取输入"""
        if self.input_win:
            self.input_win.clear()
            self.input_win.border()
            self.input_win.addstr(0, 2, " 输入区域 ")
            self.input_win.addstr(1, 1, prompt)
            self.input_win.refresh()
            
            # 获取输入
            curses.echo()
            input_str = self.input_win.getstr(2, 1, 20).decode('utf-8')
            curses.noecho()
            return input_str.strip()
    
    async def cleanup(self):
        """清理curses"""
        if self.stdscr:
            curses.nocbreak()
            self.stdscr.keypad(False)
            curses.echo()
            curses.endwin()
#######################################################

class SensorData:
    """线程安全的传感器数据容器"""
    def __init__(self):
        self.val4: Optional[float] = None
        self.val5: Optional[float] = None
        self._stop_event = asyncio.Event()

sensor_data = SensorData()

async def get_sensor_data(ui):
    """使用UI显示传感器数据"""
    sensor = SensorReader("/dev/ttyr00", 3, 1.0)
    while not sensor_data._stop_event.is_set():
        try:
            res = sensor.read_data()
            timestamp = res[1].strftime("%Y-%m-%dT%H:%M:%S.%f")
            values = res[2]
            sensor_data.val4 = values[4]
            sensor_data.val5 = values[5]
            
            # 使用UI显示而不是print
            await ui.display_sensor_data(timestamp[:-5], values[4], values[5])
            await asyncio.sleep(1)
        except Exception as e:
            await ui.display_message(f"Sensor reading error: {e}")

async def safety_monitor(ui):
    """安全监控任务"""
    while not sensor_data._stop_event.is_set():
        await asyncio.sleep(0.1)
        if sensor_data.val4 is not None and (sensor_data.val4 > 80.0 or sensor_data.val4 < -80.0):
            await ui.display_message("⚠️  val4 out of bounds! Stopping system.")
            sensor_data._stop_event.set()  # 设置停止信号
            break

async def save_to_csv(data_pairs, ui):
    """保存数据到CSV文件"""
    if data_pairs:
        filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # 设置表头
            writer.writerow(['序号', 'Steps', 'Force_Value'])
            # 写入所有数据行
            for i, (first_data, second_data) in enumerate(data_pairs, 1):
                writer.writerow([i, first_data, second_data])
        
        await ui.display_message(f"✅ 所有数据已保存到: {filename}")
        await ui.display_message(f"📊 共保存 {len(data_pairs)} 行数据")
        
        # 注意：plot_trend_matplotlib 会打开图形窗口，可能会与curses冲突
        # 你可以选择在curses清理后调用，或者注释掉这一行
        try:
            plot_trend_matplotlib(filename, x_col='Steps', y_col='Force_Value', title="Steps vs Force Value Trend Chart")
        except Exception as e:
            await ui.display_message(f"图表生成错误: {e}")
    else:
        await ui.display_message("❌ 没有数据需要保存")
    return data_pairs

def signal_handler(loop):
    print("\n接收到关闭信号，正在退出...")

    sensor_data._stop_event.set()  # 设置停止信号
    # 取消所有任务
    for task in asyncio.all_tasks():
        task.cancel()
    loop.stop()

async def main():
    motor_id = 2  # 暂定电机ID
    data_pairs = []
    
    # 初始化UI
    ui = CursesUI()
    await ui.init_ui()

    # 设置信号处理
    loop = asyncio.get_running_loop()
    for sig in [signal.SIGINT, signal.SIGTERM]:  # Ctrl+C 和 kill 信号
        loop.add_signal_handler(sig, signal_handler, loop)
    
    try:
        async with PMAC_Controller() as pmac:
            if not pmac.is_connected:
                await pmac.connect()
            
            await pmac.exec_command(f"#{motor_id}J/")

            # 启动所有任务
            sensor_task = asyncio.create_task(get_sensor_data(ui))
            safety_task = asyncio.create_task(safety_monitor(ui))

            while not sensor_data._stop_event.is_set():
                # 使用UI获取输入
                step = await ui.get_input("请输入步数: ")
                if step.lower() == 'exit':
                    break
                try:
                    await pmac.exec_command(f"#{motor_id}J={step}")
                    
                    # 等待数据稳定，同时显示等待信息
                    for i in range(10):
                        if sensor_data._stop_event.is_set():
                            await ui.display_message("🛑 安全监控触发，提前终止等待")
                            break
                        await asyncio.sleep(1)
                    
                    if sensor_data.val4 is not None:
                        data_pairs.append((step, sensor_data.val4))
                        await ui.display_message(f"✅ 记录: 步数={step}, 力值={sensor_data.val4:.3f}")
                    else:
                        await ui.display_message("⚠️ 传感器数据为空")
                except Exception as e:
                    await ui.display_message(f"Error executing command: {e}")
                    break
                    
    except Exception as e:
        await ui.display_message(f"💥 系统错误: {e}")
    finally:
        # 设置停止信号
        sensor_data._stop_event.set()
        
        # 等待任务结束
        await asyncio.sleep(0.5)  # 给任务一些时间响应停止信号
        
        # 停止电机
        try:
            async with PMAC_Controller() as pmac:
                await pmac.connect()
                await pmac.exec_command(f"#{motor_id}k")
                await ui.display_message("电机已停止")
        except Exception as e:
            await ui.display_message(f"电机停止失败: {e}")
        
        # 保存数据
        await save_to_csv(data_pairs, ui)
        
        # 清理UI
        await ui.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序出现异常: {e}")
