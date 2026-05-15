import logging

# ANSI颜色代码
COLOR_CODES = {
    "DEBUG": "\033[94m",    # 蓝色
    "INFO": "\033[92m",     # 绿色
    "WARNING": "\033[93m",  # 黄色
    "ERROR": "\033[91m",    # 红色
    "CRITICAL": "\033[95m", # 紫色
    "RESET": "\033[0m"      # 重置颜色
}

class ColoredFormatter(logging.Formatter):
    """为不同日志级别添加颜色的格式化器"""
    def format(self, record):
        # 获取原始日志消息
        message = super().format(record)
        # 根据日志级别添加颜色
        color = COLOR_CODES.get(record.levelname, COLOR_CODES["RESET"])
        return f"{color}{message}{COLOR_CODES['RESET']}"

# 配置日志记录器
def setup_logger():
    # 创建日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # 设置日志级别
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # 控制台处理器的日志级别
    
    # 创建格式化器（带时间戳和日志级别名称）
    formatter = ColoredFormatter(
        fmt='[%(asctime)s] [%(levelname)s] [%(module)s: %(funcName)s: %(lineno)d] %(message)s',  # 时间戳、日志级别、模块名 + 函数名 + 行号、日志消息
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # 将处理器添加到记录器
    logger.addHandler(console_handler)
    return logger

# 使用示例
if __name__ == "__main__":
    logger = setup_logger()
    
    logger.debug("这是一条调试信息")
    logger.info("这是一条普通信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    logger.critical("这是一条严重错误信息")
