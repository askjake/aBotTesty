#!/usr/bin/env python3
import numpy as np
import cv2
from video_health import classify_frame_signal

def make_color_bars(w=640,h=360):
    colors=[(255,255,255),(0,255,255),(255,255,0),(0,255,0),(255,0,255),(0,0,255),(255,0,0),(0,0,0)]
    img=np.zeros((h,w,3),dtype=np.uint8)
    bw=w//len(colors)
    for i,c in enumerate(colors):
        img[:,i*bw:(i+1)*bw]=c
    return img

def test_black():
    img=np.zeros((360,640,3),dtype=np.uint8)
    h=classify_frame_signal(img)
    assert h.signal_class=="black_screen"
    assert not h.active
    assert h.likely_black_screen

def test_color_bars():
    img=make_color_bars()
    h=classify_frame_signal(img)
    assert h.active
    assert h.signal_class=="color_bars", h
    assert h.likely_color_bars

def test_static_ui():
    img=np.zeros((360,640,3),dtype=np.uint8)
    cv2.rectangle(img,(50,50),(590,310),(45,45,45),-1)
    cv2.rectangle(img,(80,80),(250,140),(0,0,220),3)
    cv2.putText(img,"DISH Guide",(90,120),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2)
    h=classify_frame_signal(img)
    assert h.active
    assert h.signal_class in {"active_static_ui","active_video"}

if __name__=="__main__":
    test_black(); test_color_bars(); test_static_ui()
    print("VIDEO_HEALTH_V19_OK")
