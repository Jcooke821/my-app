import os
import cv2
import time
import math
import numpy as np
from picamera2 import Picamera2

def capture_image(exposure):
    picam2 = Picamera2()
    res = (2592, 1944)
    config = picam2.create_still_configuration(main={"format": "YUYV", "size": res, "preserve_ar": True})
    picam2.configure(config)
    picam2.start()
    picam2.set_controls({"AeEnable": 0, "ExposureTime": exposure})
    time.sleep(1.5)
    frame = picam2.capture_array()
    picam2.stop()
    picam2.close()
    return cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_YUYV)

def extract_led_roi(frame, led_coords):
    dst_size = (50, 50)
    dst_pts = np.array([[0, 0], [49, 0], [49, 49], [0, 49]], dtype="float32")
    src_pts = np.array(led_coords, dtype="float32")
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(frame, M, dst_size)

def detect_color(roi, threshold):
    avg_bgr = np.mean(roi, axis=(0, 1))
    avg_rgb = avg_bgr[::-1]
    if np.max(avg_rgb) < threshold:
        return "off", avg_rgb

    reference = {
        "red":   (255, 0, 0),
        "green": (0, 255, 0),
        "blue":  (0, 0, 255)
    }

    def dist(c1, c2):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))

    closest = min(reference.items(), key=lambda item: dist(avg_rgb, item[1]))
    return closest[0], avg_rgb

def capture_and_process_led(coords, color_name, led_num, exposure, threshold, output_dir):
    frame = capture_image(exposure)

    # Save full and downscaled image
    full_path = os.path.join(output_dir, "captured_full.jpg")
    cv2.imwrite(full_path, frame)

    downscaled = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_AREA)
    down_path = os.path.join(output_dir, "captured_downscaled.jpg")
    cv2.imwrite(down_path, downscaled)

    roi = extract_led_roi(downscaled, coords)
    roi_path = os.path.join(output_dir, f"led_{led_num}_roi_{color_name}.jpg")
    cv2.imwrite(roi_path, roi)

    return detect_color(roi, threshold)
