import smaract.smarpod as smarpod
from smaract.smarpod import Pose as Pose
import socket
import threading
import struct
import pickle
import queue
import numpy as np
import cv2
import time
from mss import mss
from utils_client import SmarPod_init, compute_dRx_dRy, pose_to_str
import random


h = SmarPod_init()

# set coordinate system
csys = Pose(0.,0.,0., 0.,0.,0.)
pHome = Pose(0.,0.,0., 0.,0.,0.)
smarpod.SetCoordinateSystem(h, csys)
# smarpod.SetPivot(h, [0, 0, 37.3e-3])
print("setting coordinate system to %s" % pose_to_str(csys))
# print("pivot point is %s" % smarpod.GetPivot(h))
smarpod.Move(h, pHome, 0, True)
# the z distance between raw pivot point of smarpod and tip of probe
while True:
    pp_x = float(input("What is the x offset of the pivot point? [0, 0.1]"))
    pp_y = float(input("What is the y offset of the pivot point? [0, 0.1]"))
    pp_z = float(input("What is the z distance between raw pivot point of smarpod and tip of probe? [0, 300]"))

    smarpod.SetPivot(h, [pp_x*1e-3, pp_y*1e-3, pp_z*1e-3])
    print("pivot point is %s" % smarpod.GetPivot(h))
    Rt = compute_dRx_dRy(angle=-10, axis=45)
    Pose_init = Pose(0, 0, 0, Rt[0], Rt[1], 0)
    smarpod.Move(h, Pose_init, 0, True)
    
    # axis = float(input("What is the rotation axis? [0,180]"))
    # angle = float(input("What is the angle between probe and normal vector of object surface?"))
    # height = float(input("What is the height of the probe? [0, 300]"))

    # # [0, 0, 37.3e-3] is the pivot point of smarpod
    # Rt = compute_dRx_dRy(angle=angle, axis=axis)

    # Pose_init = Pose(0, 0, height*1e-6, Rt[0], Rt[1], 0)
    # smarpod.Move(h, Pose_init, 0, True)

    # x_coord = float(input("What is the x coordinate of the blurriness? [-1, 1]"))
    # y_coord = -1 * float(input("What is the y coordinate of the blurriness? [-1, 1]"))

    # grad = y_coord / (x_coord + 1e-10)
    # radius = np.arctan(grad)
    # degree = np.degrees(radius)

    # rotation_axis =  degree + 90
    # sign = 1 if x_coord > 0 else -1

    # Rt_test = compute_dRx_dRy(angle=sign*10, axis=rotation_axis)
    # Pose_test = Pose(0, 0, 0, Rt[0] - Rt_test[0], Rt[1] - Rt_test[1], 0)
    # smarpod.Move(h, Pose_test, 0, True)


    move2home = input("Do you want to move to home position? 0: No, 1: Yes")
    if move2home == "1":
        smarpod.Move(h, pHome, 0, True)
    else:
        smarpod.Move(h, pHome, 0, True)
        break
    print("robot moved to home position")

# for i in range(-10, 11):
#     p = Pose(i*1e-4, 0,0,0,0,0)
#     print("moving to %s" % pose_to_str(p))
#     smarpod.Move(h, p, 0, True)
#     time.sleep(0.5)
# smarpod.Move(h, pHome, 0, True)
# for i in range(-10, 11):
#     p = Pose(0, i*1e-4,0,0,0,0)
#     print("moving to %s" % pose_to_str(p))
#     smarpod.Move(h, p, 0, True)
#     time.sleep(0.5)

# smarpod.Move(h, pHome, 0, True)
