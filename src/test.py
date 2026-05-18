import time
from datetime import datetime
import asyncio
from typing import Optional
from sensor import SensorReader
from pmac_controller import PMAC_Controller
import csv
import signal

import curses

async def main():
    sensor = SensorReader("/dev/ttyr01", 3, 1.0)
    def format_val(val: Optional[float]) -> str:
        return f"{val:.3f}" if val is not None else "None"

    async with PMAC_Controller() as pmac:
        if not pmac.is_connected:
            await pmac.connect()
        
        await pmac.exec_command("#1J/")      # 使能电机1

        await pmac.exec_command(f"#4J=0")
        while True:
            res = sensor.read_data()
            timestamp = res[1].strftime("%Y-%m-%dT%H:%M:%S.%f")
            sensor_values = res[2]
            chan1_val = sensor_values[0]
            chan2_val = sensor_values[1]
            chan3_val = sensor_values[2]
            chan4_val = sensor_values[3]
            chan5_val = sensor_values[4]
            chan6_val = sensor_values[5]
            chan7_val = sensor_values[6]
            chan8_val = sensor_values[7]
            print(f"[{timestamp[:-5]}]: chan1_val={chan1_val}, chan4_val={chan4_val}, chan5_val={chan5_val}, chan8_val={chan8_val}\n")
            await asyncio.sleep(1.0)

if __name__ == "__main__":
    async def disable_motors():
        async with PMAC_Controller() as pmac:
            if not pmac.is_connected:
                await pmac.connect() 
            await pmac.exec_command("#1k")      # 去使能电机1
            await pmac.exec_command("#2k")      # 去使能电机2
            await pmac.exec_command("#3k")      # 去使能电机3
            await pmac.exec_command("#4k")      # 去使能电机4
            await pmac.exec_command("#5k")      # 去使能电机5
            await pmac.exec_command("#6k")      # 去使能电机6
            await pmac.exec_command("#7k")      # 去使能电机7
            await pmac.exec_command("#8k")      # 去使能电机8
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("程序出现异常，正在退出...")
    finally:
        loop.run_until_complete(disable_motors())
        loop.close()