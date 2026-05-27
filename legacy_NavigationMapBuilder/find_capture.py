import cv2

print("Scanning video capture devices...")
for i in range(10):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap.isOpened():
        ret, frame = cap.read()
        w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"  Device {i}: OK — {int(w)}x{int(h)}")
        cap.release()
    else:
        print(f"  Device {i}: Not available")

print("Done.")