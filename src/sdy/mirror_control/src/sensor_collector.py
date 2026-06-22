
import time, struct, array
from multiprocessing import shared_memory, Event
from amplifier import Amplifier
from config import (AMP_DATA_BYTES, DATA_BUFF_BYTES, SENSORS_PER_AMP)
#from utils import OCS_Logger, silence_logger, PeriodicTimer
from utils import OCS_Logger, PeriodicTimer

#silence_loggers(["gsv86lib", ])


from datetime import datetime


def collector(path:str, amp_id:int, shm_name:str, stop_event:Event, start_time:float, *, interval:float=2.0, data_rate:float=1.0, debug=False):
    """单个Amplifier的子进程执行函数"""
    
    #def loop_sleeper():
    #    """固定速率-定时器"""
    #    nonlocal start_time
    #    start_time += interval
    #    curr_time = time.monotonic()
    #    diff_time = start_time - curr_time
    #    sleep_time = max(0, diff_time)
    #    if diff_time < 0:
    #        logger.warning("Loop delay: {diff_time:0.3f}s")
    #    time.sleep(sleep_time)

    logger = OCS_Logger(name=f"Amplifier[{amp_id:02d}]", debug=debug)
    amplifier = Amplifier(path=path, amp_id=amp_id, data_rate=data_rate)
    logger.info(f"amplifier is CONNECTED")
    try:
        shm = shared_memory.SharedMemory(name=shm_name)
        buffer = memoryview(shm.buf)  # 创建共享内存的内存视图对象，方便后续读写共享内存（零拷贝）
        mem_data_start = amp_id * AMP_DATA_BYTES                # 共享内存区中本放大器对应的数据存储起始位置
        mem_timestamp_start = mem_data_start + DATA_BUFF_BYTES  # 时间戳目前使用time.time(), float型。好对齐，省事，没使用int型。
        logger.info(f"shared memory is CONNECTED")

        timer = PeriodicTimer(interval, start_time)
        while not stop_event.is_set():
            #loop_sleeper()  # 修正累积时间差
            timer.waiting()

            # 读放大器数据，写入共享内存
            try:
                data = amplifier.read_data()
            except RuntimeError as err:
                logger.warning(err)
                continue
            ts = data[1].timestamp()
            values = data[2]
            if not values or len(values)!=SENSORS_PER_AMP:                    # 数据检查
                values = [float('nan')]*SENSORS_PER_AMP
            """
            ts = datetime.now().timestamp()
            values = [0.0] * 8
            values[4] = 1.23
            values[5] = 5.46
            """
            struct.pack_into(f"{SENSORS_PER_AMP}d", buffer, mem_data_start, *values)        # 8个double型，字节顺操作系统默认
            struct.pack_into(f"{SENSORS_PER_AMP}d", buffer, mem_timestamp_start, *(ts,)*SENSORS_PER_AMP)
            logger.debug(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-5]}]: {values}")
            #logger.debug(f"[{ts}]: {values}")
    except KeyboardInterrupt:
        pass
    finally:
        del buffer
        shm.close()
        #del amplifier
        logger.info(f"shared memory is CLOSED")
        logger.info(f"amplifier is CLOSED")



