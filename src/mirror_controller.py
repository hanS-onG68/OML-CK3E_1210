"""子镜闭环控制模块"""

import asyncio, time, atexit
from datetime import datetime
from multiprocessing import Process, Event
from multiprocessing.shared_memory import SharedMemory
from dataclasses import dataclass
import numpy as np
import pandas as pd

from config import (
        MIRRORS_COUNT, ACTUATORS_PER_MIRROR, SENSORS_PER_AMP, CAPACITY_SENSORS,
        TOTAL_BUFF_BYTES, SHM_NAME,
        DEFAULT_CTRL_IPS, DEFAULT_AMP_PORTS,
        MOTOR_STEPS_LIMIT, FORCE_100_UPPER, FORCE_100_LOWER, FORCE_200_UPPER, FORCE_200_LOWER, 
        FORCE_TIMEOUT,
)
from controller import Controller
from sensor_collector import collector
from utils import OCS_Logger


class Controller_Simulator:
    def __init__(self, path, ctrl_id, logger):
        self.path = path
        self.ctrl_id = ctrl_id
        self.logger = logger
        logger.info(f"Controller[{self.ctrl_id:d}]({self.path}): is CONNECTED")
    async def disconnect(self):
        await asyncio.sleep(0.01)
        self.logger.info(f"Controller[{self.ctrl_id:d}]({self.path}): is DISCONNECTED")
    async def execute_command(self, cmd):
        self.logger.info(f"Controller[{self.ctrl_id:d}]({self.path}): exec {cmd}, Started")
        await asyncio.sleep(3.0)
        self.logger.info(f"Controller[{self.ctrl_id:d}]({self.path}): exec {cmd}, Done")


@dataclass(frozen=True)
class MirrorsConfig:
    control_period_s:float = 1.0
    sensor_period_s:float = 0.05
    min_steps:int = 50
    max_steps:int = 500
    command_jitter_std = 0.1


class Mirrors:
    """子镜面形闭环控制类"""

    def __init__(self, debug=False):
        self.debug = debug
        self.logger = OCS_Logger(name="MIRRORS", debug=self.debug)

        # 控制标签
        self.stop_event = Event()
        self.close_loop = False

        # 闭环矩阵
        self.Target = np.zeros((MIRRORS_COUNT, ACTUATORS_PER_MIRROR))       # 力维持目标值，由上层提供(主动光学/查表)
        self.Force = np.zeros((MIRRORS_COUNT, ACTUATORS_PER_MIRROR))        # 力传感器数据
        self.Force_TS = np.zeros((MIRRORS_COUNT, ACTUATORS_PER_MIRROR))     # 力传感器时间戳
        self.Error = np.zeros((MIRRORS_COUNT, ACTUATORS_PER_MIRROR))        # 目标值与实际值之间的偏差
        self.K_p = np.loadtxt("settings/Coefficient_K_p.csv", delimiter=',', skiprows=1)    # 增益
        self.Threshold = np.loadtxt("settings/Threshold.csv", delimiter=',', skiprows=1)    # 阈值
        self.Force_limit_pos = np.ones((MIRRORS_COUNT, ACTUATORS_PER_MIRROR))*100.0         # 力值上限
        self.Force_limit_neg = np.ones((MIRRORS_COUNT, ACTUATORS_PER_MIRROR))*-100.0        # 力值下限
        #self.Force_limit_pos[:, 0::2] = 200.0
        self.Force_timeout = FORCE_TIMEOUT

        self.Steps = np.zeros_like(self.Target)
        self.steps_limit = MOTOR_STEPS_LIMIT

        #self.Available = np.full((MIRRORS_COUNT, ACTUATORS_PER_MIRROR), False, dtype=bool)
        #self._mask_blocked("settings/Blocked.csv")
        self.Available = np.full((MIRRORS_COUNT, ACTUATORS_PER_MIRROR), False, dtype=bool)

        """
        self.Target[0, 0] = 15.0
        self.Target[0, 1] = 15.0
        
        self.Available[0, 0] = True
        self.Available[0, 1] = True
        """

        self.Target.fill(15.0)
        self.Available[0, :8] = True


        # 映射索引
        mapping = np.loadtxt("settings/Actuator_Mapping.csv", delimiter=',', skiprows=1, dtype=int)
        self.actuator_id, self.controller_id, self.axis_id, self.amplifer_id, self.channel_id = mapping.T    # 配置表拆成5个列向量
        self._sensor_idx = self.amplifer_id*SENSORS_PER_AMP + self.channel_id                                # 逻辑促动器空间到物理传感器空间的映射

        # 共享内存
        self.shm = self._create_shm()
        self._buffer = np.ndarray((CAPACITY_SENSORS*2,), dtype=np.float64, buffer=self.shm.buf)  # CAPACITY_SENSORS=8*19
        self._buffer.fill(np.nan)
        self._data =  self._buffer[:CAPACITY_SENSORS]       # 传感器数据视图，零拷贝
        self._timestamp = self._buffer[CAPACITY_SENSORS:]   # 传感器时间戳视图，零拷贝

        # 控制器
        self._create_controllers()
        """
        self.controller_ips = self._load_hardware_config("settings/Controller_IP.csv", col=1, defaults=DEFAULT_CTRL_IPS)
        self.Controllers = dict()
        for ctrl_id in np.unique(self.controller_id[self.Available.ravel()]):
            ctrl_ip = self.controller_ips[ctrl_id]
            controller = 1#Controller(ctrl_ip, ctrl_id)
            self.Controllers[ctrl_id] = controller
            self.logger.info(f"Controllers[{ctrl_id}] is CONNECTED to {ctrl_ip}")
        """

        # 传感器
        self._create_amplifiers()
        """
        self.amplifer_ports = self._load_hardware_config("settings/Amplifier_Port.csv", col=1, defaults=DEFAULT_AMP_PORTS)
        self.start_time = time.monotonic()
        self.Amplifiers = dict()
        for amp_id in np.unique(self.amplifer_id[self.Available.ravel()]):
            port = self.amplifer_ports[amp_id]
            worker = Process(
                    target=collector,
                    args=(port, amp_id, SHM_NAME, self.stop_event, self.start_time,),
                    kwargs={'interval':1.0, 'data_rate':1.0, 'debug':debug, },
            )
            worker.start()
            self.Amplifiers[amp_id] = worker
            self.logger.info(f"Amplifiers[{amp_id}] is CONNECTED to {port}")
        """

    async def close(self):
        if self.stop_event and not self.stop_event.is_set():
            self.stop_event.set()       # 发信号，让采集子进程自己停止
        for worker in self.Amplifiers.values():
            worker.join(timeout=2.0)    # 回收采集子进程
        self.Amplifiers.clear()
        tasks = [ctrl.disconnect() for ctrl in self.Controllers.values()]
        await asyncio.gather(*tasks)
        self.Controllers.clear()

        if hasattr(self, '_buffer'):    # 回收共享内存引用
            del self._data
            del self._timestamp
            del self._buffer
        if self.shm:
            self.shm.close()
            self.shm.unlink()           # 回收共享内存
            self.shm = None

    def _create_shm(self) -> SharedMemory:
        # created shared memory in /dev/shm/
        #self._clean_shm()
        shm = SharedMemory(create=True, name=SHM_NAME, size=TOTAL_BUFF_BYTES)
        atexit.register(self._clean_shm)
        self.logger.info(f"Created shared memory '{SHM_NAME}'")
        return shm

    def _clean_shm(self) -> None:
        try:
            SharedMemory(name=SHM_NAME).unlink()  # 回调时已经处于资源销毁阶段，成员self.shm可能已经被回收了，所以此处不使用self.shm.unlink()?
        except FileNotFoundError:
            return
        except Exception as err:
            self.logger.warning(f"Failed to unlink old shared memory '{SHM_NAME}': {err}!r")
        #self.logger.warning(f"Clean up shared memory '{SHM_NAME}'")    # atexit执行时已经没有logger了。


    def _create_controllers(self):
        self.controller_ips = self._load_hardware_config("settings/Controller_IP.csv", col=1, defaults=DEFAULT_CTRL_IPS)
        self.Controllers = dict()
        for ctrl_id in np.unique(self.controller_id[self.Available.ravel()]):
            ctrl_ip = self.controller_ips[ctrl_id]
            controller = Controller(ctrl_ip, ctrl_id, )
            asyncio.get_event_loop().create_task(controller.connect())
            #controller = Controller_Simulator(ctrl_ip, ctrl_id, self.logger)
            self.Controllers[ctrl_id] = controller
            self.logger.info(f"Controllers[{ctrl_id}] is CONNECTED to {ctrl_ip}")

    def _create_amplifiers(self):
        self.amplifer_ports = self._load_hardware_config("settings/Amplifier_Port.csv", col=1, defaults=DEFAULT_AMP_PORTS)
        self.start_time = time.monotonic()
        self.Amplifiers = dict()
        for amp_id in np.unique(self.amplifer_id[self.Available.ravel()]):
            port = self.amplifer_ports[amp_id]
            worker = Process(
                    target=collector,
                    args=(port, amp_id, SHM_NAME, self.stop_event, self.start_time,),
                    kwargs={'interval':1.0, 'data_rate':1.0, 'debug':self.debug, },
            )
            worker.start()
            self.Amplifiers[amp_id] = worker
            self.logger.info(f"Amplifiers[{amp_id}] is CONNECTED to {port}")
    


    def _mask_blocked(self, path):
        """处理屏蔽力促动器单元"""
        try:
            blocked = np.loadtxt(path, delimiter=',', comments='#', skiprows=1, dtype=int)
        except OSError:
            return      # 没有Blocked.csv文件
        if blocked.size == 0:
            return  # Blocked.csv文件为空记录
        if blocked.ndim == 1:
            blocked = blocked.reshape(1, -1)    # Blocked.csv文件中只有一行记录
        if blocked.shape[1] != 2:
            raise ValueError("Blocked.csv 格式错误，应为两列：mirror_id, actuator_id")
        rows, cols = blocked.T  #blocked[:, 0], blocked[:, 1]
        self.Available[rows, cols] = False

    @staticmethod
    def _load_hardware_config(filepath, col, defaults):
        try:
            data = np.loadtxt(filepath, delimiter=',', dtype=str, skiprows=1, comments='#')
        except OSError:
            return defaults.copy()
        if data.ndim == 1:                    # .ndim: 返回数组的维度数;
            data = data.reshape(1, -1)        # 1行N列
        loaded = data[:, col].tolist()        # 提取指定列的所有行数据，再转换成Python原生的字符串列表
        loaded = [s.strip() for s in loaded]  # 对loaded列表中的每个字符串做「首尾空白清洗」，得到干净的字符串列表----自动删除字符串首尾的所有空白字符：包括普通空格、换行符\n、制表符\t、回车符\r等，字符串中间的空格不会被删除
        n = len(defaults)
        if len(loaded) < n:
            loaded.extend(defaults[len(loaded):])
        elif len(loaded) > n:
            loaded = loaded[:n]
        return loaded

    def get_force(self):
        """获取最新力传感器数据和时间戳 -- 花式索引，一次拷贝，1.17us"""
        self.Force = self._data[self._sensor_idx].reshape(MIRRORS_COUNT, ACTUATORS_PER_MIRROR)
        self.Force_TS = self._timestamp[self._sensor_idx].reshape(MIRRORS_COUNT, ACTUATORS_PER_MIRROR)
        return self.Force, self.Force_TS

    async def run(self):
        try:
            while True:
                await asyncio.sleep(5)
                now_ts = time.time()
                
                # 获取传感器最新数据
                self.Force, self.Force_TS = self.get_force()
                
                # 全矩阵运算，效率不高，但意思清晰。如果要追求效率，可以先用条件卡住矩阵
                Error = self.Target - self.Force
                raw = Error * self.K_p    # 达到目标需要的步数
                
                # 严格条件筛选
                valid_mask = (self.Available &
                        ~np.isnan(self.Force) &
                        (self.Target>self.Force_limit_neg) &
                        (self.Target<self.Force_limit_pos) &
                        (self.Force_TS - now_ts < self.Force_timeout)
                )
                need_move_mask = valid_mask & (np.abs(Error) > self.Threshold)
                
                # 转换成各促动器电机补偿步数
                self.Steps = np.where(need_move_mask, np.clip(raw, -self.steps_limit, self.steps_limit), 0.0)

                
                with pd.option_context('display.max_rows', 4, 'display.max_columns', 16, 'display.precision', 2):
                    #self.logger.info(f"self.Target:\n{pd.DataFrame(self.Target)}\n")
                    self.logger.info(f"self.Force:\n{pd.DataFrame(self.Force)}\n")
                    #self.logger.info(f"self.Error:\n{pd.DataFrame(Error)}\n")
                    self.logger.info(f"raw_Steps:\n{pd.DataFrame(raw)}\n")
                    self.logger.info(f"self.Steps:\n{pd.DataFrame(self.Steps)}\n")
                    
                # 控制电机运行
                cmds = self.build_motor_commands(self.Steps)
                print(f"CMDS= {cmds}")
                await self.execute_commands(cmds)
                
                
                """
                #error = np.where(valid_mask, self.Target-self.Force, 0.0)
                #need_move_mask = valid_mask & (np.abs(error)>self.Threshold)
                #raw = error[need_move_mask] * self.K_p[need_move_mask]
                #clipped = np.clip(raw, -self.steps_limit, self.steps_limit)
                #self.Steps.fill(0)
                #self.Steps[need_move_mask] = clipped
                """
                """
                with np.printoptions(precision=2, suppress=False, linewidth=300):
                    self.logger.warning(f"self.Error:\n{Error}")
                    self.logger.warning(f"raw_Steps:\n{raw}")
                    self.logger.warning(f"self.Steps:\n{self.Steps}")
                """
                

                """
                self.Steps = np.zeros((MIRRORS_COUNT, ACTUATORS_PER_MIRROR))
                # 卡住目标力值上下限
                valid_mask = (self.Available &
                        ~np.isnan(self.Force) &
                        (self.Target>self.Force_limit_neg) &
                        (self.Target<self.Force_limit_pos))
                error = np.where(valid_mask, self.Target - self.Force, 0.0)
                need_move_mask = valid_mask & (np.abs(error)>self.Threshold)
                steps_raw = error[need_move_mask] * self.K_p[need_move_mask]
                #steps_raw = (self.Target[valid_mask] - self.Force[valid_mask]) * self.K_p[valid_mask]

                # 卡住单轮电机步数正负限
                self.Steps[valid_mask] = np.clip(steps_raw, -self.steps_limit, self.steps_limit)
                print(f"AAAAA:Target:     {self.Target[valid_mask]}")
                print(f"AAAAA:Force:      {self.Force[valid_mask]}")
                print(f"AAAAA:Error:      {error}")
                print(f"AAAAA:Steps_Raw:  {steps_raw}")
                print(f"AAAAA:Steps_Real: {self.Steps[valid_mask]}")
                cmds = self.build_motor_commands(self.Steps)
                print(f"AAAAA:Commands:   {cmds}\n\n")
                """


        except KeyboardInterrupt:
            pass

    def build_motor_commands(self, steps):
        commands = dict()
        for ctrl_id in range(MIRRORS_COUNT):
            axes = np.nonzero(self.Steps[ctrl_id])[0]
            if len(axes) == 0:
                continue
            parts = [f"#{axis_id+1:02d}J:{int(self.Steps[ctrl_id, axis_id])}" for axis_id in axes]
            #parts = [f"#{axis_id:02d}J={self.Steps[ctrl_id, axis_id]:0.3f}" for axis_id in axes]
            cmd = " ".join(parts)
            commands[ctrl_id] = cmd
        return commands

    async def execute_commands(self, commands):
        if not commands:
            return
        tasks = []
        for ctrl_id, cmd in commands.items():
            #tasks.append(asyncio.create_task(self.Controllers[ctrl_id].execute_command(cmd)))
            tasks.append(asyncio.create_task(self.Controllers[ctrl_id]._exec_command(cmd)))
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=3.2)


    async def moter_one(self, ctrl_id:int, axis_id:int, target:int):
        cmd = "#{axis_id}J={target:d}"
        await self.Controllers[ctrl_id]._exec_command(cmd)



        

    """
        active_mask = np.ones((6, 25), dtype=bool)
        active_mask[bad_sensor_pos] = False

        Gain_matrix = np.full((6, 25), default_gain)
        Gain_matrix[centrain_actuators] = custom_gain

        # P control
        Error = Target - Measured
        maks = (np.abs(Error) > Threshold) & active_mask
        Steps = Error[mask] * Gain_matrix[mask]

        # PI control
        dt = 2.0
        Error = Target - Measured
        I_error += Error * dt
        I_error = np.clip(I_error, I_post_max, I_minus_max)
        Steps_raw = Error*Gain_matrix + Ki*I_error
        Steps = np.clip(Steps_raw, min_steps, max_steps)






        tasks = []
        for ctrl_id, axis in zip(np.where(np.abs(Error)>Threshold)[0]:
            task = asyncio.create_task(self.move_motor(ctrl_id, axis))
            tasks.append(task)
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=2.0)

    """



if __name__ == "__main__":
    mirrors = Mirrors()#debug=True)
    loop = asyncio.get_event_loop()
    loop.create_task(mirrors.run())
    try:
        #asyncio.run(mirrors.run())
        loop.run_forever()
    except (Exception, KeyboardInterrupt):
        loop.run_until_complete(mirrors.close())



