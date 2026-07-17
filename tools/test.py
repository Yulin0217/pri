import cv2
import numpy as np
from mss import mss

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

while True:
    
    x = int(input("What is the x coordinate of top-left corner of sceenshot? [0, 1920]"))
    y = int(input("What is the y coordinate of top-left corner of sceenshot? [0, 1080]"))
    height = int(input("What is the height of the screenshot? [0, 1080]"))
    width = int(input("What is the width of the screenshot? [0, 1920]"))

    img = capture_partial_screen(y, x, height=height, width=width)
    cv2.imshow('raw', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

