import cv2
import numpy as np


def main():
    print(f"OpenCV version: {cv2.__version__}")

    # Тест камери
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("✅ Camera OK")
        ret, frame = cap.read()
        if ret:
            print(f"✅ Frame captured: {frame.shape}")
        cap.release()
    else:
        print("❌ Camera failed")


if __name__ == "__main__":
    main()
