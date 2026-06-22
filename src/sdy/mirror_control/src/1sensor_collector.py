


import time, struct, array
from multiprocessing import Process, shared_memory, managers
from amplifier import Amplifier
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")









def read_amplifier(amp_id):
    import random
    return [random.uniform(-90.0, 90.0) for _ in range(8)]


def amplifer_worker(amp_id, shm_name, sensor_data_bytes, timestamp_data_bytes, interval=1.0):
    port = f"/dev/ttyr{amp_id:02d}"
    try:
        amplifier = Amplifier(path=port, group_id=amp_id, datarate=1.0)
    except Exception as err:
        logging.error(f"Amplifier {amp_id} failed to open serial port '{port}'")
        return

    sensors_per_amp = 8
    bytes_per_float = 8
    amp_sensor_bytes = amp_timestamp_bytes = sensors_per_amp * bytes_per_float

    sensor_mem_start = sensor_data_bytes + amp_id * amp_sensor_bytes
    sensor_mem_end = sensor_mem_start + amp_sensor_bytes

    timestamp_mem_start = timestamp_data_bytes + amp_id * amp_timestamp_bytes
    timestamp_mem_end = timestamp_mem_start + amp_timestamp_bytes

    try:
        shm = sm.shared_memory.SharedMemory(name=shm_name)
    except FileNotFoundError:
        logging.error(f"Amplifier {amp_id} failed to open shared memory '{shm_name}'")
        return

    mem = memoryview(shm.buf)

    next_time = time.monotonic()
    while not stop_event.is_set():
        try:
            data = amplifier.read_data()
            print(f"DATA: {data}")

        except Exception as err:
            pass

        next_time += interval
        curr_time = time.monotonic()
        sleep_time = max(0, next_time-curr_time)
        time.sleep(sleep_time)

    shm.close()







def main():
    N_SENSORS = 152
    sensor_mem_bytes = N_SENSORS * 8
    timestamp_mem_bytes = N_SENSORS * 8
    shm_size = sensor_mem_bytes + timestamp_mem_bytes

    with managers.SharedMemoryManager() as smm:
        shm = smm.SharedMemory(size=shm_size)
        shm_name = shm.name
        np.ndarray((N_SENSORS,), dtype=np.float64, buffer=shm.buf, offset=0).fill(0.0)
        np.ndarray((N_SENSORS,), dtype=np.float64, buffer=shm.buf, offset=sensor_mem_bytes).fill(0.0)
        workers = []
        for amp_id in range(1):
            worker = Process(target=amplifer_worker, args=(amp_id, shm_name, 0, sensor_mem_bytes, 1.0))
            worker.start()
            workers.append(worker)
            
        time.sleep(3)
        while True:
            sensor_data = np.ndarray((N_SENSORS,), dtype=np.float64, buffer=shm.buf, offset=0)
            timestamp_data = np.ndarray((N_SENSORS,), dtype=np.float64, buffer=shm.buf, offset=sensor_bytes)
                




