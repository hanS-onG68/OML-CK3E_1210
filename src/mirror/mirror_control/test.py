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

kp_file = resources.files("mirror.mirror_control").joinpath("settings/Coefficient_K_p.csv")
K_p = np.loadtxt(kp_file, delimiter=',', skiprows=1)    # 增益
print(f"K_p = {K_p}, K_p.shape = {K_p.shape}")

target_file = resources.files("mirror.mirror_control").joinpath("settings/Initial_Target.csv") 
target_data = np.loadtxt(target_file, delimiter=',', dtype=str, skiprows=1, comments='#')
initial_target_force = np.char.strip(target_data[:, 1]).astype(float)
Target = initial_target_force.reshape(6, 25)
print(f"Target = {Target}, Target.shape = {Target.shape}")