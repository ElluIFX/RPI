from __future__ import print_function
import pyzbar.pyzbar as pyzbar
import numpy as np
import cv2

def decode(im) :
  # Find barcodes and QR codes
  decodedObjects = pyzbar.decode(im)

  # Print results
  for obj in decodedObjects:
    print('Type : ', obj.type)
    print('Data : ', obj.data,'\n')

  return decodedObjects

# Display barcode and QR code location
def display(im, decodedObjects):

  # Loop over all decoded objects
  for decodedObject in decodedObjects:
    points = decodedObject.polygon

    # If the points do not form a quad, find convex hull
    if len(points) > 4 :
      hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
      hull = list(map(tuple, np.squeeze(hull)))
    else :
      hull = points;

    # Number of points in the convex hull
    n = len(hull)

    # Draw the convext hull
    for j in range(0,n):
      cv2.line(im, hull[j], hull[ (j+1) % n], (255,0,0), 3)

  # Display results
  cv2.imshow("Results", im);

# Main
if __name__ == '__main__':

  # Read image
  cap = cv2.VideoCapture(0)
  ret, frame = cap.read()
  rows, cols, channels = frame.shape
  print(cols, rows, channels)
  while(1):
    ret,frame = cap.read()
    cv2.imshow('usb camera', frame)  
    decodedObjects = decode(frame)
    display(frame, decodedObjects)
    k = cv2.waitKey(50)
    if (k == ord('q')):
      break
  cap.release()
  cv2.destroyAllWindows()