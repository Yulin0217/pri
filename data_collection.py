# Copyright (c) 2020 SmarAct GmbH

# Programming example for the SmarPod Python API.

# THIS  SOFTWARE, DOCUMENTS, FILES AND INFORMATION ARE PROVIDED 'AS IS'
# WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING,
# BUT  NOT  LIMITED  TO,  THE  IMPLIED  WARRANTIES  OF MERCHANTABILITY,
# FITNESS FOR A PURPOSE, OR THE WARRANTY OF NON-INFRINGEMENT.
# THE  ENTIRE  RISK  ARISING OUT OF USE OR PERFORMANCE OF THIS SOFTWARE
# REMAINS WITH YOU.
# IN  NO  EVENT  SHALL  THE  SMARACT  GMBH  BE  LIABLE  FOR ANY DIRECT,
# INDIRECT, SPECIAL, INCIDENTAL, CONSEQUENTIAL OR OTHER DAMAGES ARISING
# OUT OF THE USE OR INABILITY TO USE THIS SOFTWARE.
#
# WHEN RUNNING, THIS PROGRAMMING EXAMPLE WILL MOVE THE POSITIONER. 
# ENSURE THAT THIS CAN'T CAUSE COLLISIONS. THE POSITIONER MUST HAVE
# SUFFICIENT SPACE TO MOVE OVER ITS FULL RANGE.


import smaract.smarpod as smarpod
from smaract.smarpod import Pose as Pose
import numpy as np
import time
import math
from mss import mss
import cv2
import os
import json
from time import strftime, localtime
from utils_client import SmarPod_init


def check_lib_compatibility():
    """
    checks that the major version numbers of the Python API and the
    loaded shared library are the same to avoid errors due to 
    incompatibilites.
    raises a RuntimeError if the major version numbers are different.
    """
    vapi = smarpod.api_version
    vlib = smarpod.GetDLLVersion()
    if vapi[0] != vlib[0]:
        raise RuntimeError("incompatible python api and library version")    

def print_info():
    vapi = smarpod.api_version
    print("api version = %s.%s.%s" % (vapi[0], vapi[1], vapi[2]))
    vlib = smarpod.GetDLLVersion()
    print("lib version = %s.%s.%s" % (vlib[0], vlib[1], vlib[2]))

def print_controllers():
    syslist = smarpod.FindSystems().splitlines()
    for sys in syslist:
        print("controllers found:\n%s\n" % sys)    

def pose_to_str(pose):
    return "%s,%s,%s,%s,%s,%s" %  (
        pose.positionX, pose.positionY, pose.positionZ,
        pose.rotationX, pose.rotationY, pose.rotationZ)

def check_pose_list(h,list):
    """
    returns True if all poses in list are reachable
    """
    for pose in list:
        if not smarpod.IsPoseReachable(h,pose):
            return False
    return True

def move_sequence(h,seq):
    """
    moves to each pose in the list seq
    """
    for pose in seq:
        print("moving to %s" % pose_to_str(pose))
        smarpod.Move(h,pose,0,True)

def compute_dx_dy_dz_dRx_dRy(rotation_angle, rotation_axis, height):
    '''
    rotation_angle: the angle to rotate at specifc rotation axis
    rotation_aixs: the angle between rotation axis and x axis
    height: the distance between probe tip and raw pivot point in smarpod  
    '''

    d = height * math.sin(np.abs(rotation_angle * math.pi / 180.))
    dx = np.sign(rotation_angle) * d * math.cos(rotation_axis * math.pi / 180.)
    dy = - np.sign(rotation_angle) * d * math.sin(rotation_axis * math.pi / 180.)
    dz = height * (1 - math.cos(np.abs(rotation_angle * math.pi / 180.)))

    dRx = math.atan(dy / height) / math.pi * 180
    dRy = - math.atan(dx / height) / math.pi * 180

    return (dx, dy, dz, dRx, dRy)

def capture_partial_screen(top, left, width, height):
    with mss() as sct:
        monitor = {"top": top, "left": left,
                   "width": width, "height": height}
        img = sct.grab(monitor)
        img_np = np.array(img)
        # print(img_np.shape)
        img_RGB = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
        # cv2.imshow('raw', img_gray)

    return img_RGB


def capture_image():
    # image capturing
    img = capture_partial_screen(45,1118,350,350)

    return img

def save_to_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

check_lib_compatibility()
print_info()

# change model to the model code of your SmarPod model code before
# starting the program
model = 10001

# uncomment the following line to show available controllers
#print_controllers()

# change the locator of your positioner controller: if it is connected
# over USB, "usb:ix:0" should work. If if it connected over ethernet,
# use the network locator format and replace the ip address by the one
# of your controller. (for MCS 1 controllers append the port number
# :5000, for MCS 2 controllers, when specifying the locator with an IPv4 
# address, no port should be appended. alternatively, for MCS 2 the
# serial number can be used in the locator)
locator = "usb:ix:0"
#locator = "network:ip:198.168.1.200:5000"  # MCS 1
#locator = "network:ip:198.168.1.200"       # MCS 2
#locator = "network:sn:MCS2-000001234"      # MCS 2

# set to True to perform a calibration of the positioner sensors
do_calibrate = False
# the sensor power mode to set
sensor_mode = smarpod.SensorPowerMode.ENABLED

# enable z-safe ref method to prefer z-negative direction
# (this will fail with a FEATURE_UNAVAILABLE error if the SmarPod model 
#  doesn't support the selected method)
ref_zsafe = False
# perform a referencing even if SmarPod is already the referenced state
force_referencing = False


# open the connection to the SmarPod device.
# on success, a handle is returned, else an execption is thrown
# if Open raises an exception with ErrorCode.SYSTEM_CONFIGURATION
# the model code and the controller configuration don't match.
# smarpod.ConfigureController(model, locator)
h = smarpod.Open(model, locator)
print("device opened successfully")

# set the frequency used for referencing and calibration
smarpod.Set_ui(h, smarpod.Property.FREF_AND_CAL_FREQUENCY, 8000)

# if do_calibrate is True, perform calibration
if do_calibrate:
    print("calibrating...")
    smarpod.Calibrate(h)

# if not referenced, perform referencing
do_referencing = force_referencing or not smarpod.IsReferenced(h)
if do_referencing:
    # set referencing method and parameters
    if (ref_zsafe):
        smarpod.Set_ui(h, smarpod.Property.FREF_METHOD, smarpod.FrefMethod.ZSAFE)
        smarpod.Set_ui(h, smarpod.Property.FREF_ZDIRECTION, smarpod.Direction.NEGATIVE)
    else:
        smarpod.Set_ui(h, smarpod.Property.FREF_METHOD, smarpod.DEFAULT)
    print("referencing...")
    smarpod.FindReferenceMarks(h)

smarpod.SetSensorMode(h, sensor_mode)

mstat = smarpod.GetMoveStatus(h)
print("movement status = %s (%s)" % (smarpod.MoveStatus(mstat), mstat))

smarpod.Stop(h)

mstat = smarpod.GetMoveStatus(h)
print("movement status = %s (%s)" % (smarpod.MoveStatus(mstat), mstat))


# move sequence of poses

# set speed and maximum closed-loop piezo frequency
smarpod.SetSpeed(h, 1, 3e-3)
smarpod.SetMaxFrequency(h, 18500)

# pivot point should move with the top plate: set to RELATIVE mode
smarpod.Set_ui(h, smarpod.Property.PIVOT_MODE, smarpod.PivotMode.RELATIVE)
# set pivot point
smarpod.SetPivot(h,[0,0,0])

save_dir = os.path.join("./", input("Save data to ?"))

# os.makedirs(save_dir, exist_ok=True)
# # the z distance between raw pivot point of smarpod and tip of probe
# height = 19e-3
# # height = 60e-3

# # height = 20e-3

# # the rotaton axis at the x-y plane 
# rotation_axis = 125.

# # rotation angle
# rotation_angle = 10

csys = Pose(0.,0.,0., 0.,0.,0.)
smarpod.SetCoordinateSystem(h, csys)
print("setting coordinate system to %s" % pose_to_str(csys))
# probe rotation along fixed axis
pHome = Pose(0, 0, 0, 0, 0, 0)

# # # probe tip and end calibration code
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

# smarpod.Move(h, pHome, 0 ,True)

# clear and blurry image collection
# Poses = {}
# smarpod.Move(h, pHome, 0, True)
# print("collect clear pCLE image (press ENTER)")
# input()
folder_name = 'clear_blur_data' + strftime('%Y-%m-%H-%M-%S', localtime(time.time()))
folder_path = os.path.join(save_dir, folder_name)
os.makedirs(folder_path, exist_ok=True)

##############################################
###### static robot arm, manual capture ######
################################################
# idx = 0
# while True:
#     img = capture_image()
#     cv2.imwrite(os.path.join(folder_path, "{:04d}.jpg".format(idx)), img=img)
#     idx += 1
#     time.sleep(0.5)
#     # press 'q' to quit the while loop
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break 

##############################################
###### Robotic movement cross pattern and pCLE Focus ######
################################################
Poses = {}
idx = 0
for i in range(-10, 11):
    for j in range(-10, 11):
        for n in range(0, 401, 10):
            pose = Pose(i*1e-4, j*1e-4, 0,0,0,0) #-n*1e-6, 0, 0, 0)
            smarpod.Move(h, pose, 0, True)
            Poses[idx] = pose_to_str(pose)
            # time.sleep(0.1)
            img = capture_image()
            # time.sleep(0.1)
            cv2.imwrite(os.path.join(folder_path, "{}_{}_{}.jpg".format(i, j, n)), img=img)     
            # idx += 1
smarpod.Move(h, pHome, 0, True)

json_path = os.path.join(folder_path, 'trajectory.json')
save_to_json(json_path, Poses)

##############################################


# print("collect blur pCLE image caused by distance (press ENTER when you are ready to capture!)")
# input()
# # distance blur
# for i in range(10, 301, 10):
#     p = Pose(0,0,-i* 1e-6, 0,0,0)
#     smarpod.Move(h, p, 0, True)
#     time.sleep(0.5)
#     img = capture_image()
#     cv2.imwrite(os.path.join(save_dir, "{:04d}.jpg".format(idx)), img=img)
#     Poses[idx] =[0,0,i]
#     idx += 1
# smarpod.Move(h, pHome, 0, True)

# print("collect clear pCLE image caused by orientation (press ENTER when you are ready to capture!)")
# input()
# # orientation blur
# for j in range(0, 181, 45):
#     for n in range(-10, 11, 5):
#         Rt = compute_dx_dy_dz_dRx_dRy(rotation_angle=n, rotation_axis=j, height=height)
#         p = Pose(Rt[0], Rt[1], Rt[2], Rt[3], Rt[4], 0)
#         smarpod.Move(h, p, 0, True)
#         time.sleep(0.5)
#         img = capture_image()
#         cv2.imwrite(os.path.join(save_dir, "{:04d}.jpg".format(idx)), img=img)
#         Poses[idx] =[j, n, 0]
#         idx += 1
#     smarpod.Move(h, pHome, 0, True)
#     time.sleep(0.5)

# smarpod.Move(h, pHome, 0, True)



# p = Pose(Rt[0], Rt[1], Rt[2], Rt[3], Rt[4], 0)
# smarpod.Move(h, p, 0, True)
# input()
# cv2.imwrite(os.path.join(save_dir, "{:04d}.jpg".format(idx)), img=img)     
# smarpod.Move(h, pHome, 0, True)



##############################################
###### Robotic movement spiral scan ######
################################################
# spiral scanning
# print("Start Spiral Scanning!!!!!!!!!!!")
# Poses = {}
# idx = 0
# for i in np.arange(0, 12, 0.1):
#     x = i*math.cos(i*math.pi)*1e-4
#     y = i*math.sin(i*math.pi)*1e-4
#     p = Pose(x, y, 0, 0, 0, 0)
#     smarpod.Move(h, p, 0, True)
#     print("Probe move to %s" % pose_to_str(p))
#     Poses[idx] = pose_to_str(p)
#     img = capture_image()
#     cv2.imwrite(os.path.join(save_dir, "{:04d}.jpg".format(idx)), img=img)
#     print(os.path.join(folder_path, "{:04d}.jpg".format(idx)))
#     idx += 1
#     time.sleep(0.25)

# smarpod.Move(h, pHome, 0, True)

# json_path = f'{folder_path}/trajectory.json'
# save_to_json(json_path, Poses)
###################################################





# # query current pose (should be close to pHome)
# pose = smarpod.GetPose(h)
# print("pose = %s" % pose_to_str(pose))

# smarpod.Stop(h)
# print("closing device")
# smarpod.Close(h)
# h = None