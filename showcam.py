#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import cv2
import numpy as np
name = 0
cap = cv2.VideoCapture(0)
 
#cap.set(3,1920/2)
#cap.set(4,1080/2)
ret, frame = cap.read()
rows, cols, channels = frame.shape
print(cols, rows, channels)
 
 
while(1):
        ret,frame = cap.read()
        cv2.imshow('usb camera', frame)

        k = cv2.waitKey(50)
        if (k == ord('q')):
            break
        elif(k == ord('s')):
            #name = input('name:')
            name += 1
            filename = r'~/camera/cam_' + str(name) + '.jpg'
            cv2.imwrite(filename, frame)
            print(filename)
            #break 
cap.release()
cv2.destroyAllWindows()
