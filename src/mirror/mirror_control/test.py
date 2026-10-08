import asyncio
from mirror.amplifier.domestic_amplifier import Amplifier as amp
from contextlib import AsyncExitStack
import numpy as np
from importlib import resources

amp_file = resources.files("mirror.mirror_control").joinpath("settings/Actuator_Mapping.csv") 
data = np.loadtxt(amp_file, delimiter=',', dtype=str, skiprows=1, comments='#')
# dev_data = np.zeros(len(data), dtype=str)
# print(f"data = {data}-{data.shape}, dev_data = {dev_data}-{dev_data.shape}")
data = np.char.strip(data[:,:]).astype(int)
actuator_id, controller_id, axis_id, amplifier_id, channel_id = data.T
print(f"actuator_id = {actuator_id}, controller_id = {controller_id}, axis_id = {axis_id}, amplifier_id = {amplifier_id}, channel_id = {channel_id}")

