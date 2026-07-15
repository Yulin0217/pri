# Laptop (Client)

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
import os
import json
import random

HOST = '172.30.28.159'  # Replace with the AGX station's IP address
PORT = 12334   # Port to connect to

# Queue to hold distances received from the server
distance_queue = queue.Queue()
angle_queue = queue.Queue()
axis_queue = queue.Queue()

# Create a shutdown event
shutdown_event = threading.Event()

def send_data(sock, signal):
    while not shutdown_event.is_set():
        # Capture image
        image = capture_image()
        image = cv2.resize(image, (224, 224), interpolation=cv2.INTER_CUBIC)

        # Encode the image to JPEG format
        _, img_encoded = cv2.imencode('.jpg', image)
        img_bytes = img_encoded.tobytes()

        # Serialize the data
        if signal['value'] == 1:
            data = pickle.dumps({'image': img_bytes, 'signal': signal['value']})
            signal['value'] = 0
        else:
            data = pickle.dumps({'image': img_bytes, 'signal': signal['value']})
        # print("signal value is %s" % signal['value'])
        data_len = struct.pack('!I', len(data))
        sock.sendall(data_len + data)

        # Control the sending rate
        time.sleep(0.05)

def send_data_controller(sock, signal):
    while not shutdown_event.is_set():
        # Capture image
        image = capture_image()
        image = cv2.resize(image, (224, 224), interpolation=cv2.INTER_CUBIC)


        # Encode the image to JPEG format
        _, img_encoded = cv2.imencode('.jpg', image)
        img_bytes = img_encoded.tobytes()

        # Serialize the data
        data = pickle.dumps({'image': img_bytes, 'signal': signal['value']})

        data_len = struct.pack('!I', len(data))
        sock.sendall(data_len + data)

        # Control the sending rate
        time.sleep(0.05)

def receive_data(sock):
    while not shutdown_event.is_set():
        # Receive the length of the incoming data
        data_len_bytes = sock.recv(4)
        if not data_len_bytes:
            print('Disconnected from server')
            break
        data_len = struct.unpack('!I', data_len_bytes)[0]

        # Receive the actual data based on the length
        data = b''
        while len(data) < data_len:
            packet = sock.recv(data_len - len(data))
            if not packet:
                break
            data += packet
        if not data:
            break

        # Deserialize the data
        received_data = pickle.loads(data)
        distance = received_data['distance']
        angle = received_data['angle']
        axis = received_data['axis']

        distance_queue.put(distance)
        angle_queue.put(angle)
        axis_queue.put(axis)

def robot_position_update(signal, clear_signal, robot_state, position_idx, mosaic_trajectory):
        x_y_z = mosaic_trajectory[position_idx]
        robot_state['t'][0] = x_y_z[0]
        robot_state['t'][1] = x_y_z[1]

        
        if x_y_z[2] != mosaic_trajectory[position_idx-1][2] and position_idx > 0:
            robot_state['t'][2] = x_y_z[2]
        else:
            pass
        # robot_state['t'][2] = x_y_z[2]
        p = Pose(robot_state['t'][0], robot_state['t'][1], robot_state['t'][2],
                  robot_state['R'][0], robot_state['R'][1], robot_state['R'][2])
        print("robot change to {} position".format(position_idx))
        smarpod.Move(h, p, 0, True)
        time.sleep(0.5)
        position_idx += 1
        signal['value'] = 1

        clear_signal['value'] = 0
        return position_idx

            

def robot_control(sock, signal, clear_signal,robot_state, STEP, position_idx, mosaic_trajectory):
    while True:
        if STEP == 0:
            state_data[STEP] = {
            'timestamp': time.time(),
            'position': {
                'x': robot_state['t'][0],
                'y': robot_state['t'][1],
                'z': robot_state['t'][2]
            },
            'rotation': {
                'rx': robot_state['R'][0],
                'ry': robot_state['R'][1],
                'rz': robot_state['R'][2],
            }
            }
            STEP += 1
            # Save to file
            filename = os.path.join(folder_name, "state.json")

            with open(filename, 'w') as f:
                json.dump(state_data, f, indent=4)


        distance = distance_queue.get()
        angle = angle_queue.get()
        axis = axis_queue.get()
        if distance != 0.0 and angle == 0.0:
            robot_state['t'][-1] += (distance * 1e-6)
            # if robot_state['t'][-1] > 50e-6:
            #     robot_state['t'][-1] = 50e-6
            p = Pose(robot_state['t'][0], robot_state['t'][1], robot_state['t'][2],
                      robot_state['R'][0], robot_state['R'][1], robot_state['R'][2])
            print("robot state is %s" % robot_state)
            print("robot move to %s" % pose_to_str(p))
        elif angle != 0.0 and distance == 0.0:
            if np.abs(angle) > 10:
                angle = 10 * np.sign(angle)
            Rt = compute_dRx_dRy(angle=angle, axis=axis)
            # robot_state['R'][0] += Rt[0]
            # robot_state['R'][1] += Rt[1]
            if np.sign(Rt[0]) != np.sign(robot_state['R'][0]) and np.abs(Rt[0]) >= np.abs(robot_state['R'][0]):
                robot_state['R'][0] = 2 * random.random()
            elif np.sign(Rt[0]) != np.sign(robot_state['R'][0]) and np.abs(Rt[0]) < np.abs(robot_state['R'][0]):
                robot_state['R'][0] += Rt[0]
            elif np.sign(Rt[0]) == np.sign(robot_state['R'][0]) and np.abs(Rt[0]) >= np.abs(robot_state['R'][0]):
                robot_state['R'][0] = 2 * random.random()
            elif np.sign(Rt[0]) == np.sign(robot_state['R'][0]) and np.abs(Rt[0]) < np.abs(robot_state['R'][0]):
                robot_state['R'][0] -= Rt[0]
            if np.sign(Rt[1]) != np.sign(robot_state['R'][1]) and np.abs(Rt[1]) >= np.abs(robot_state['R'][1]):
                robot_state['R'][1] = 2 * random.random()
            elif np.sign(Rt[1]) != np.sign(robot_state['R'][1]) and np.abs(Rt[1]) < np.abs(robot_state['R'][1]):
                robot_state['R'][1] += Rt[1]
            elif np.sign(Rt[1]) == np.sign(robot_state['R'][1]) and np.abs(Rt[1]) >= np.abs(robot_state['R'][1]):
                robot_state['R'][1] = 2 * random.random()
            elif np.sign(Rt[1]) == np.sign(robot_state['R'][1]) and np.abs(Rt[1]) < np.abs(robot_state['R'][1]):
                robot_state['R'][1] -= Rt[1]
            p = Pose(robot_state['t'][0], robot_state['t'][1], robot_state['t'][2],
                      robot_state['R'][0], robot_state['R'][1], robot_state['R'][2])
            print("robot state is %s" % robot_state)
            print("robot move to %s" % pose_to_str(p))
                
        else:
            p = Pose(robot_state['t'][0], robot_state['t'][1], robot_state['t'][2],
                      robot_state['R'][0], robot_state['R'][1], robot_state['R'][2])
            if clear_signal['mosaic'] == True:
                clear_signal['value'] = 1
            pass  # No action needed when distance is 0

        
        smarpod.Move(h, p, 0, True)
        # Save robot state to a file
        
        # Create state data to save
        state_data[STEP] = {
            'timestamp': time.time(),
            'position': {
                'x': robot_state['t'][0],
                'y': robot_state['t'][1],
                'z': robot_state['t'][2]
            },
            'rotation': {
                'rx': robot_state['R'][0],
                'ry': robot_state['R'][1],
                'rz': robot_state['R'][2], 
                'axis': axis
            }
        }
        STEP += 1
        # Save to file
        filename = os.path.join(folder_name, "state.json")
        img = capture_partial_screen(420, 1050, 600, 600)
        cv2.imwrite(os.path.join(folder_name, "images/img_%04d.png" % STEP), img)

        with open(filename, 'w') as f:
            json.dump(state_data, f, indent=4)


        # print(Rt)
        time.sleep(0.5)
        if clear_signal['mosaic'] == True:
            if  position_idx >= len(mosaic_trajectory) and clear_signal['value'] == 1:
                print("robot reach the end of trajectory")
                print("shuting down")
                shutdown_event.set()
                break
            elif clear_signal['value'] == 1:
                position_idx = robot_position_update(signal, clear_signal, robot_state, position_idx, mosaic_trajectory)
                
            elif clear_signal['value'] == 0:
                signal['value'] = 1
                
        else:
            signal['value'] = 1

            
def robot_random_move(sock, ):
    while True:
        # the z distance between raw pivot point of smarpod and tip of probe
        height = 36.4e-3
        axis = random.random() * 180
        angle = 10
        distance = random.random() * 2e-4
        # Rt = compute_dx_dy_dz_dRx_dRy(rotation_angle=angle, rotation_axis=axis, height=height)
        # p = Pose(Rt[0], Rt[1], Rt[2], Rt[3], Rt[4], 0)
        # print("Rotate in axis %s for %s degree" % (axis, angle))
        # smarpod.Move(h, p, 0, True)
        # time.sleep(0.5)
        # smarpod.Move(h, pHome, 0, True)
        # print("Move to home position")
        # time.sleep(0.5)
        p = Pose(0., 0., -distance, 0., 0., 0.)
        smarpod.Move(h, p, 0, True)
        print("Move up to {:.2f}um".format(distance*1e6))
        time.sleep(0.5)
        smarpod.Move(h, pHome, 0, True)
        print("Move to home position")
        time.sleep(0.5)

def keyboard_listener():
    # Listens for keyboard input and sets the shutdown event when 'q' is pressed
    print("Press 'q' to quit the client!!!")
    while not shutdown_event.is_set():
        user_input = input()
        if user_input.lower() == 'q':
            print("Shutdown signal received")
            shutdown_event.set()
            break


def capture_partial_screen(top, left, width, height):
    with mss() as sct:
        monitor = {"top": top, "left": left,
                   "width": width, "height": height}
        img = sct.grab(monitor)
        img_np = np.array(img)
        # print(img_np.shape)
        img_RGB = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
        # cv2.imshow('raw', img_gray)

    return img_RGB

def capture_image():
    # image capturing
    img = capture_partial_screen(45,1118,350,350)

    return img

def main():
    global signal
    signal = {'value': 1}             # Shared signal variable for robot movement
    global clear_signal
    position_idx = 0
    global robot_state
    global h  # handle for smarpod
    global pHome # home position
    global state_data
    state_data = {}

    global STEP
    STEP = 0

    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
    global folder_name
    # Create a folder with the current timestamp
    folder_name = f"robot_state_{current_time}"
    os.makedirs(folder_name, exist_ok=True)
    os.makedirs(os.path.join(folder_name, "images"), exist_ok=True)

    
    # Initialize the SmarPod
    h = SmarPod_init()

    # set coordinate system
    csys = Pose(0.,0.,0., 0.,0.,0.)
    pHome = Pose(0.,0.,0., 0.,0.,0.)
    smarpod.SetCoordinateSystem(h, csys)
    smarpod.SetPivot(h, [0, 0, 37.4e-3])
    print("setting coordinate system to %s" % pose_to_str(csys))
    print("pivot point is %s" % smarpod.GetPivot(h))


    print("setting coordinate system to %s" % pose_to_str(csys))
    smarpod.Move(h, pHome, 0, True)
    mode = input("which mode do you want to use? 0 for visual servoing with mosaicing, 1 for visual servoing mode, 2 for controller mode")

    if mode == "0":
        print("Visual servoing with mosaicing mode")
        clear_signal = {'value': 0, 'mosaic': True}
        mosaic_trajectory = []
        # compute spiral x, y trajectory
        step_a = np.arange(0, 5, 0.4)
        step_b = np.arange(5, 8, 0.1)
        steps = np.concatenate((step_a, step_b))
        z = 0
        n_start = 14
        for n, i in enumerate(steps):
            x = i * np.cos(i * np.pi) * 1e-4
            y = i * np.sin(i * np.pi) * 1e-4
            if i >= 3:
                if x < 0 and y < 0:
                    z = -100e-6
                elif x > 0 and y > 0:
                    z = -100e-6
                else:
                    z = -50e-6
            else:
                z = 0

            # mosaic_trajectory.append([x, y, z, 0, 0])
            mosaic_trajectory.append([x, y, 0, 0, 0])
            # if n % 4 == 0 and i > 3:
            #     z = -200 *1e-6
            #     grad = (-y) / (x + 1e-10)
            #     if np.abs(grad) > 2:
            #         axis = 90
            #     elif np.abs(grad) < (1/2):
            #         axis = 0
            #     elif np.sign(grad) > 0 and (1/2) <= np.abs(grad) <= 2:
            #         axis = 45
            #     elif np.sign(grad) < 0 and (1/2) <= np.abs(grad) <= 2:
            #         axis = 135
            #     angle = round(10 - i) * np.sign(grad)
            # else:
            #     z = 0
            #     axis = 0
            #     angle = 0
            # dx, dy = compute_dRx_dRy(angle=angle, axis=axis)
            # mosaic_trajectory.append([x, y, z, dx, dy])
        t_init = [0, 0, 0]
        R_init = [0, 0, 0]


        robot_state = {'t': t_init, 'R': R_init}
        
        # Start the keyboard listener thread
        threading.Thread(target=keyboard_listener, daemon=True).start()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((HOST, PORT))
            except Exception as e:
                print(f"Failed to connect to server: {e}")

            # Start threads for sending data, receiving distance, and robot control
            send_data_thread = threading.Thread(target=send_data, args=(s, signal), daemon=True)
            receive_data_thread = threading.Thread(target=receive_data, args=(s,), daemon=True)
            robot_control_thread = threading.Thread(target=robot_control, args=(s, signal, clear_signal, robot_state, STEP, position_idx, mosaic_trajectory), daemon=True)

            send_data_thread.start()
            receive_data_thread.start()
            robot_control_thread.start()

            # Keep the main thread alive
            try:
                while not shutdown_event.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                print("KeyboardInterrupt received. Shutting down!!!!!!!!!!")

            finally:
                shutdown_event.set()
                if h != None:
                    smarpod.Move(h, pHome, 0, True)
                    smarpod.Stop(h)
                    print("closing device")
                    smarpod.Close(h)
                    h = None

                send_data_thread.join()
                receive_data_thread.join()
                robot_control_thread.join()

                print("Client has been shut down!!!!!!!!!!!!!")


    elif mode == "1":
        print("Visual servoing mode")
        clear_signal = {'value': 0, 'mosaic': False}
        axis = float(input("What is the rotation axis? [0,180]"))
        angle = float(input("What is the angle between probe and normal vector of object surface? [-10, 10]"))
        z_distance = float(input("What is the distance between probe and object surface? [0, 200]"))
        Rt = compute_dRx_dRy(angle=angle, axis=axis)
        mosaic_trajectory = None

        t_init = [0, 0, -z_distance * 1e-6]
        R_init = [Rt[0], Rt[1], 0]
        Pose_init = Pose(t_init[0], t_init[1], t_init[2], R_init[0], R_init[1], R_init[2])
        print("initial pose is %s" % pose_to_str(Pose_init))
        smarpod.Move(h, Pose_init, 0, True)
        time.sleep(1)

        robot_state = {'t': t_init, 'R': R_init}
        
        # Start the keyboard listener thread
        threading.Thread(target=keyboard_listener, daemon=True).start()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((HOST, PORT))
            except Exception as e:
                print(f"Failed to connect to server: {e}")

            # Start threads for sending data, receiving distance, and robot control
            send_data_thread = threading.Thread(target=send_data, args=(s, signal), daemon=True)
            receive_data_thread = threading.Thread(target=receive_data, args=(s,), daemon=True)
            robot_control_thread = threading.Thread(target=robot_control, args=(s, signal, clear_signal, robot_state, STEP, position_idx, mosaic_trajectory), daemon=True)

            send_data_thread.start()
            receive_data_thread.start()
            robot_control_thread.start()

            # Keep the main thread alive
            try:
                while not shutdown_event.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                print("KeyboardInterrupt received. Shutting down!!!!!!!!!!")

            finally:
                shutdown_event.set()
                if h != None:
                    smarpod.Move(h, pHome, 0, True)
                    smarpod.Stop(h)
                    print("closing device")
                    smarpod.Close(h)
                    h = None
                s.close()
                send_data_thread.join()
                receive_data_thread.join()
                robot_control_thread.join()

                print("Client has been shut down!!!!!!!!!!!!!")
    elif mode == "2":
        print("Controller mode")
        clear_signal = {'value': 0, 'mosaic': False}
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((HOST, PORT))
            except Exception as e:
                print(f"Failed to connect to server: {e}")

            # Start threads for sending data
            send_data_thread = threading.Thread(target=send_data_controller, args=(s, signal), daemon=True)
            # robot_random_move_thread = threading.Thread(target=robot_random_move, args=(s,), daemon=True)

            send_data_thread.start()
            # robot_random_move_thread.start()
            # Keep the main thread alive
            try:
                while not shutdown_event.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                print("KeyboardInterrupt received. Shutting down!!!!!!!!!!")

            finally:
                shutdown_event.set()
                if h != None:
                    smarpod.Move(h, pHome, 0, True)
                    smarpod.Stop(h)
                    print("closing device")
                    smarpod.Close(h)
                    h = None

                send_data_thread.join()
                # robot_random_move_thread.join()

                print("Client has been shut down!!!!!!!!!!!!!")
    else:
        print("Invalid mode")


            

if __name__ == '__main__':
    main()