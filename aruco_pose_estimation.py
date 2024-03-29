#!/usr/bin/python3
"""
This demo calculates multiple things for different scenarios.

Here are the defined reference frames:

TAG:
                A y
                |
                |
                |tag center
                O---------> x

CAMERA:


                X--------> x
                | frame center
                |
                |
                V y

F1: Flipped (180 deg) tag frame around x axis
F2: Flipped (180 deg) camera frame around x axis

The attitude of a generic frame 2 respect to a frame 1 can obtained by calculating euler(R_21.T)

We are going to obtain the following quantities:
    > from aruco library we obtain tvec and Rct, position of the tag in camera frame and attitude of the tag
    > position of the Camera in Tag axis: -R_ct.T*tvec
    > Transformation of the camera, respect to f1 (the tag flipped frame): R_cf1 = R_ct*R_tf1 = R_cf*R_f
    > Transformation of the tag, respect to f2 (the camera flipped frame): R_tf2 = Rtc*R_cf2 = R_tc*R_f
    > R_tf1 = R_cf2 an symmetric = R_f


"""

import numpy as np
import cv2
import cv2.aruco as aruco
import sys, time, math
import serial
import time

#--- Define Tag
#id_to_find  = 72
marker_size  = 10#7- [cm]
theta = -70*np.pi/180 # Rotation autour de x_camera en radian
# Offsets lies à la position de la camera
offsetX = 0
offsetY = -100
offsetZ = 0
offset=np.zeros(3)
ArucoInit=42

posArucoInitDesiree=np.array([0.0, 0, 0])
          
FRAME_WIDTH = 1280 #640#1280
FRAME_HEIGHT = 720 #480#720

#rot_camera_to_table = np.array([[1,0,0],[0,np.cos(theta),np.sin(theta)],[0,-np.sin(theta),np.cos(theta)]])
TEMPS_BOUSSOLE = 25 #25 secondes après on est sûr qu'ell est arrétée
ser = serial.Serial('/dev/ttyUSB0',57600 ,timeout=1) #/dev/ttyAMA0 /dev/ttyUSB0
color = -1

   
        
        

#------------------------------------------------------------------------------
#------- ROTATIONS https://www.learnopencv.com/rotation-matrix-to-euler-angles/
#------------------------------------------------------------------------------
# Checks if a matrix is a valid rotation matrix.
def isRotationMatrix(R):
    Rt = np.transpose(R)
    shouldBeIdentity = np.dot(Rt, R)
    I = np.identity(3, dtype=R.dtype)
    n = np.linalg.norm(I - shouldBeIdentity)
    return n < 1e-6


# Calculates rotation matrix to euler angles
# The result is the same as MATLAB except the order
# of the euler angles ( x and z are swapped ).
def rotationMatrixToEulerAngles(R):
    assert (isRotationMatrix(R))

    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])

    singular = sy < 1e-6

    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0

    return np.array([x, y, z])


# A partir d'une image en gray scale découpe la zone d'intéret et détermine la couleur par une moyenne
def get_boussole_color(gray,threshold=127,cutmX=435,cutpX=620,cutmY=138,cutpY=162):
    
	# Decoupe de l'image
    crop_img = gray[cutmY:cutpY, cutmX:cutpX]
	
	#apply threshold
    thresh = cv2.threshold(crop_img, threshold, 255, cv2.THRESH_BINARY)[1]
    cv2.imshow("THRESH", thresh)
    if np.mean(thresh) < threshold:
        return "Black"
    return "White"

def send_data(identifiant,x,y,z,theta,calcul_time):
    data = "i {} {} {:.2f} {:.2f} {:.2f} {:.2f} {:.2f}\n".format(color,identifiant[0],x,y,z,theta,calcul_time)
    print(data)
    #ser.write(str(calcul_time).encode('ascii'))
    ser.write(data.encode('ascii'))
    print("fin send_data")


#--- Get the camera calibration path
calib_path  = "camera_02/"
camera_matrix   = np.loadtxt(calib_path+'cameraMatrix.txt', delimiter=',')
camera_distortion   = np.loadtxt(calib_path+'cameraDistortion.txt', delimiter=',')

#--- 180 deg rotation matrix around the x axis
R_flip  = np.zeros((3,3), dtype=np.float32)
R_flip[0,0] = 1.0
R_flip[1,1] =-1.0
R_flip[2,2] =-1.0

#--- Define the aruco dictionary
aruco_dict  = aruco.getPredefinedDictionary(aruco.DICT_4X4_250)
parameters  = aruco.DetectorParameters_create()


#--- Capture the videocamera (this may also be a video or a picture)
cap = cv2.VideoCapture(0)
#-- Set the camera size as the one it was calibrated with
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH) #1280 640
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT) #720  480

#-- Font for the text in the image
font = cv2.FONT_HERSHEY_PLAIN


def init():
    succes = False
    while succes == False:
        ret, frame = cap.read()
        global rot_camera_to_table, offset

        #-- Convert in gray scale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) #-- remember, OpenCV stores color images in Blue, Green, Red

        #print(get_boussole_color(gray))
        #-- Find all the aruco markers in the image
        corners, ids, rejected = aruco.detectMarkers(image=gray, dictionary=aruco_dict, parameters=parameters, cameraMatrix=camera_matrix, distCoeff=camera_distortion)
        #corners, ids, rejected = aruco.detectMarkers(image=gray, dictionary=aruco_dict,parameters=parameters)
        print('__Init__')
        print(corners, 'ids:', ids)
        noAr=[-1]
        if type(ids) != np.ndarray:
            print("No aruco detected")
            time.sleep(1)
            continue
        for i,idAr in enumerate(ids):
            #print('trvé :',i, idAr)
            if (idAr==[ArucoInit]):
                noAr[0]=i
                break
        aruco_size=10
        print(noAr, corners[noAr[0]])
        #cv2.imshow('im', frame)
        if (noAr[0]>=0):
            ret = aruco.estimatePoseSingleMarkers([corners[noAr[0]]], aruco_size, camera_matrix, camera_distortion)
            
            #-- Unpack the output, get only the first
            rvec, tvec = ret[0][0,0,:], ret[1][0,0,:]
            
            #-- Draw the detected marker and put a reference frame over it
            #aruco.drawDetectedMarkers(frame, corners)
            #aruco.draiwAxis(frame, camera_matrix, camera_distortion, rvec, tvec, 10)

            #-- Print the tag position in camera frame
            #str_position = "MARKER Position x=%4.0f  y=%4.0f  z=%4.0f"%(tvec[0], tvec[1], tvec[2])
            #cv2.putText(frame, str_position, (0, 100), font, 1, (0, 255, 0), 2, cv2.LINE_AA)

            #-- Obtain the rotation matrix tag->camera
            R_ct    = np.matrix(cv2.Rodrigues(rvec)[0])
            R_tc    = R_ct.T 
            
            if (idAr==ArucoInit):
                    rot_camera_to_table=np.array(R_flip*R_tc)
                    offset=np.dot(rot_camera_to_table, tvec) -posArucoInitDesiree
            print("mat rotation\n",rot_camera_to_table,"\n offset\n", offset) 
            #--- Display the frame
            cv2.imshow('frame', frame)
            
        else:
            #--- use 'q' to quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return
            continue
        succes = True




init()


print("mat rotation\n",rot_camera_to_table,"\n offset\n", offset)


while True:
    temps = time.time()
    #-- Read the camera frame
    ret, frame = cap.read()

    #-- Convert in gray scale
    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) #-- remember, OpenCV stores color images in Blue, Green, Red


    print(get_boussole_color(gray))
    if get_boussole_color(gray) == "Black":
        color = 0
    else:
        color = 1
    #-- Find all the aruco markers in the image
    corners, ids, rejected = aruco.detectMarkers(image=gray, dictionary=aruco_dict, parameters=parameters, cameraMatrix=camera_matrix, distCoeff=camera_distortion)
    #corners, ids, rejected = aruco.detectMarkers(image=gray, dictionary=aruco_dict,parameters=parameters)
    print('____')
    if ids is not None:
        
        #-- ret = [rvec, tvec, ?]
        #-- array of rotation and position of each marker in camera frame
        #-- rvec = [[rvec_1], [rvec_2], ...]    attitude of the marker respect to camera frame
        #-- tvec = [[tvec_1], [tvec_2], ...]    position of the marker in camera frame
        ret = aruco.estimatePoseSingleMarkers(corners, marker_size, camera_matrix, camera_distortion)

        #-- Unpack the output, get only the first
        rvec, tvec = ret[0][0,0,:], ret[1][0,0,:]

        #-- Draw the detected marker and put a reference frame over it
        aruco.drawDetectedMarkers(frame, corners)
        aruco.drawAxis(frame, camera_matrix, camera_distortion, rvec, tvec, 10)

        #-- Print the tag position in camera frame
        str_position = "MARKER Position x=%4.0f  y=%4.0f  z=%4.0f"%(tvec[0], tvec[1], tvec[2])
        cv2.putText(frame, str_position, (0, 100), font, 1, (0, 255, 0), 2, cv2.LINE_AA)

        #-- Obtain the rotation matrix tag->camera
        R_ct    = np.matrix(cv2.Rodrigues(rvec)[0])
        R_tc    = R_ct.T
        
        #-- Get the attitude in terms of euler 321 (Needs to be flipped first)
        roll_marker, pitch_marker, yaw_marker = rotationMatrixToEulerAngles(R_flip*R_tc)

        #-- Print the marker's attitude respect to camera frame
        str_attitude = "MARKER Attitude r=%4.0f  p=%4.0f  y=%4.0f"%(math.degrees(roll_marker),math.degrees(pitch_marker),
                            math.degrees(yaw_marker))
        cv2.putText(frame, str_attitude, (0, 150), font, 1, (0, 255, 0), 2, cv2.LINE_AA)


        #-- Now get Position and attitude f the camera respect to the marker
        pos_camera = -R_tc*np.matrix(tvec).T

        str_position = "CAMERA Position x=%4.0f  y=%4.0f  z=%4.0f"%(pos_camera[0], pos_camera[1], pos_camera[2])
        cv2.putText(frame, str_position, (0, 200), font, 1, (0, 255, 0), 2, cv2.LINE_AA)

        #-- Get the attitude of the camera respect to the frame
        roll_camera, pitch_camera, yaw_camera = rotationMatrixToEulerAngles(R_flip*R_tc)
        str_attitude = "CAMERA Attitude r=%4.0f  p=%4.0f  y=%4.0f"%(math.degrees(roll_camera),math.degrees(pitch_camera),
                            math.degrees(yaw_camera))
        cv2.putText(frame, str_attitude, (0, 250), font, 1, (0, 255, 0), 2, cv2.LINE_AA)
        
        # Conversion dans la base table
        Pos = np.dot(rot_camera_to_table,tvec[0:3])
        #Pos[0] -= offsetX
        #Pos[1] -= offsetY
        #Pos[2] -= offsetZ
        Pos-=offset
        send_data(ids[0],Pos[0],Pos[1],Pos[2],math.degrees(yaw_marker),time.time()-temps)
        ser.flush()
        #while ser.in_waiting != 0:
        #    print(ser.readline().decode('ascii'))
        print(time.time()-temps)




    #--- Display the frame
    #cv2.imshow('frame', frame)

    #--- use 'q' to quit
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        cap.release()
        cv2.destroyAllWindows()
        break


