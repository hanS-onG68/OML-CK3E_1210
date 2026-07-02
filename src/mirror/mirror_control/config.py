


MIRRORS_COUNT = 6
ACTUATORS_PER_MIRROR = 25
TOTAL_ACTUATORS = ACTUATORS_PER_MIRROR * MIRRORS_COUNT  # 力促动器总数量


AMPLIFIER_COUNT = 19
SENSORS_PER_AMP = 8
CAPACITY_SENSORS = SENSORS_PER_AMP * AMPLIFIER_COUNT    # 放大器总接口数(不是实际用了多少个接口)

BYTES_PER_FLOAT = 8
AMP_DATA_BYTES = BYTES_PER_FLOAT * SENSORS_PER_AMP          # 单个放大器数据连续共享内存区大小
AMP_TIMESTAMP_BYTES = BYTES_PER_FLOAT * SENSORS_PER_AMP     # 单个放大器时间戳连续共享内存区大小
DATA_BUFF_BYTES = BYTES_PER_FLOAT * CAPACITY_SENSORS        # 全部放大器数据连续共享内存区大小，也是时间戳区的起点
TIMESTAMP_BUFF_BYTES = BYTES_PER_FLOAT * CAPACITY_SENSORS   # 全部放大器数据连续共享内存区大小，也是时间戳区的起点
TOTAL_BUFF_BYTES = DATA_BUFF_BYTES + TIMESTAMP_BUFF_BYTES

SHM_NAME = "QUEST_Mirrors_Control"


DEFAULT_CTRL_IPS = [f"192.168.0.{200+i}" for i in range(6)]
# DEFAULT_AMP_PORTS = [f"/dev/ttyr{i:02d}" for i in range(19)]      # 进口放大器
DEFAULT_AMP_PORTS = [f"192.168.0.{i}" for i in range(102, 121, 1)]  # 国产放大器



FORCE_100_UPPER = 100
FORCE_100_LOWER = -100
FORCE_200_UPPER = 200
FORCE_200_LOWER = -200
MOTOR_STEPS_LIMIT = 5000

FORCE_TIMEOUT = 2.0


Actuator2Pon_Map = {
    1: {    # 1号边缘子镜：逻辑驱动器编号到物理位置编号的映射
        0:  "7", 1:  "1b", 2:  "11", 3:  "6a", 4:  "16", 5:  "3a", 6:  "10", 7:  "5a", 8:  "15", 9:  "2a",
        10: "9", 11: "4a", 12: "14", 13: "1a", 14: "8",  15: "6b", 16: "19", 17: "3b", 18: "13", 19: "5b", 20: "18", 21: "2b", 22: "12", 23: "4b", 24: "17"
    },
    2: {    # 2号边缘子镜：逻辑驱动器编号到物理位置编号的映射
        0:  "7", 1:  "3a", 2:  "11", 3:  "5a", 4:  "16", 5:  "2a", 6:  "10", 7:  "4a", 8:  "15", 9:  "1a",
        10: "9", 11: "6b", 12: "14", 13: "3b", 14: "8",  15: "5b", 16: "19", 17: "2b", 18: "13", 19: "4b", 20: "18", 21: "1b", 22: "12", 23: "6a", 24: "17"
    }
}


