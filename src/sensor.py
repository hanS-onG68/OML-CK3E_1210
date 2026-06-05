import time, os
from datetime import datetime
from logger import setup_logger

from gsv86lib import gsv86



class SensorReader:
    """力传感器数据读取类"""

    def __init__(self, path:str, group_id:int, datarate=10.0, logger=None):
        """初始化函数

        Args:
            path(str): 传感器文件
            group_id(int): 组编号，MOXA串口网口转换器
            datarate(float): 传感器内部采样频率
            logger(utils.Logger): 日志记录器
        """
        self.group_id = group_id
        self.logger = setup_logger()
        self.datarate = datarate

        self.com = gsv86(path, baudrate=115200)
        self.com.writeDataRate(self.datarate)
        self.com.StartTransmission()
        
        if self.logger:
            self.logger.info(f"Group[{self.group_id}, datarate={self.datarate}]({path}): is start transmission")
        # TODO: 这个是我自己凑的经验公式，等待时间应该是采第一批数据的时间间隔，和datarate有关，datar
        time.sleep(3.0/self.datarate)

    def __del__(self):
        if self.com and self.com.transmissionIsRunning:
            self.com.StopTransmission()
        if self.logger:
            self.logger.info(f"Group[{self.group_id}]: is stop transmission")

    def read_data(self):
        """获取GSV8-DS的一组数据"""
        if not self.com or not self.com.transmissionIsRunning:
            raise RuntimeError(f"Group[{self.group_id}]: is not READY")
        data = self.com.ReadValue()
        if not data.data:
            if self.logger:
                self.logger.warning(f"Group[{self.group_id}]: fetch data: None")
            return (self.group_id, datetime.now(), None)
        # data.data = [ str(timestamp),
        #               {'channel0': xxx, .... , 'channel7': xxx},
        #               bool(isInputOverload), bool(isSixAxisError) ]
        timestamp = datetime.fromisoformat(data.data[0])
        # TODO: 这里本可以写成getattr(data, f'getChannel{i}')()
        values = []
        values.append(data.getChannel1())
        values.append(data.getChannel2())
        values.append(data.getChannel3())
        values.append(data.getChannel4())
        values.append(data.getChannel5())
        values.append(data.getChannel6())
        values.append(data.getChannel7())
        values.append(data.getChannel8())
        result = (self.group_id, timestamp, values)
        if self.logger:
            self.logger.debug(f"Group[{self.group_id}]: fetch data: {result}")
        return result
    
