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
    async with PMAC_Controller() as pmac:
        if not pmac.is_connected:
            await pmac.connect()
        await pmac.exec_command(f"#1k")
        await pmac.exec_command(f"#2k")
        await pmac.exec_command(f"#3k")
        await pmac.exec_command(f"#4k")
        await pmac.exec_command(f"#5k")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("程序出现异常，正在退出...")
    finally:
        loop.close()