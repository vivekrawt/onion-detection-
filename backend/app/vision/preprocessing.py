"""Controlled-background preprocessing; CLIP performs its own tensor normalization."""
import cv2
import numpy as np


def preprocess(image, config):
    rgb = np.asarray(image.convert("RGB"))
    scale = min(1.0, config.MAX_IMAGE_SIDE / max(rgb.shape[:2]))
    if scale < 1:
        rgb = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    # Keep the original colors for CLIP; adjustments affect segmentation only.
    adjusted = np.clip(rgb.astype(np.float32) * config.BRIGHTNESS_GAIN, 0, 255).astype(np.uint8)
    adjusted = cv2.GaussianBlur(adjusted, (5, 5), 0)
    return rgb, cv2.cvtColor(adjusted, cv2.COLOR_RGB2LAB), cv2.cvtColor(adjusted, cv2.COLOR_RGB2HSV)
