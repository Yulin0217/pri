import smaract.smarpod as smarpod
from smaract.smarpod import Pose as Pose
import numpy as np
import time
import math

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

# def compute_dx_dy_dz_dRx_dRy(rotation_angle, rotation_axis, height):
#     '''
#     rotation_angle: the angle to rotate at specifc rotation axis
#     rotation_aixs: the angle between rotation axis and x axis
#     height: the distance between probe tip and raw pivot point in smarpod  
#     '''

#     d = height * math.sin(np.abs(rotation_angle * math.pi / 180.))
#     dx = np.sign(rotation_angle) * d * math.cos(rotation_axis * math.pi / 180.)
#     dy = - np.sign(rotation_angle) * d * math.sin(rotation_axis * math.pi / 180.)
#     dz = height * (1 - math.cos(np.abs(rotation_angle * math.pi / 180.)))

#     dRx = math.atan(dy / height) / math.pi * 180
#     dRy = - math.atan(dx / height) / math.pi * 180

#     return (dx, dy, dz, dRx, dRy)


def compute_dRx_dRy(angle, axis):
    '''
    convert arbitrary axis rotation to x and y axis rotation
    Ra(dRa) = Ry(dRy) * Rx(dRx)
    where:
        Ra(dRa) = rotation about arbitrary axis
        Ry(dRy) = rotation about y axis
        Rx(dRx) = rotation about x axis
    sin(dRx) = sin(angle) * cos(axis)
    sin(dRy) = sin(angle) * sin(axis)
    Parameters
    ----------
    angle: float
        angle in dgerees
    axis: float
        rotation axis with respect to the x axis
        0: x axis
        90: y axis
    '''

    # convert to radians
    angle = math.radians(angle)
    axis = math.radians(axis)

    sindRx = math.sin(angle) * math.cos(axis)
    sindRy = math.sin(angle) * math.sin(axis)

    dRx = math.degrees(math.asin(sindRx))
    dRy = math.degrees(math.asin(sindRy))
    return dRx, dRy


def SmarPod_init():
    check_lib_compatibility()
    print_info()

    model = 10001
    locator = "usb:ix:0"

    # set to True to perform a calibration of the positioner sensors
    temp = input("Do calibration or not? 0: False, 1: True ==> ")
    do_calibrate = (temp == '1')
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
    
    
    return h
