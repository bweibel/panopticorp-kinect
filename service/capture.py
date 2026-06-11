import freenect
import numpy as np
import cv2


def depth_callback(dev, depth, timestamp):
    # depth is uint16 mm; 0 = invalid
    display = (depth / 4096.0 * 255).astype(np.uint8)
    display = cv2.applyColorMap(display, cv2.COLORMAP_BONE)
    cv2.imshow("depth", display)
    if cv2.waitKey(1) == ord("q"):
        raise freenect.Kill


def run():
    print("Opening Kinect... (Ctrl-C or press q to quit)")
    cv2.namedWindow("depth", cv2.WINDOW_NORMAL)
    freenect.runloop(depth=depth_callback)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
