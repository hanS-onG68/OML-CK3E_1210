import numpy as np

s = ["#123  ", " 56#"]

t = [ss.strip('#') for ss in s]

print(t)