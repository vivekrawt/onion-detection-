"""Separate foreground candidates, not a trained onion detector.

The image border must be clear background. Touching bulbs may merge and other
foreground objects can be mistaken for onions; inspect the overlay every time.
"""
import cv2
import numpy as np


def segment(lab, hsv, marker_polygons, config):
    border = np.concatenate((lab[0], lab[-1], lab[:, 0], lab[:, -1]))
    background = np.median(border, axis=0)
    distance = np.linalg.norm(lab.astype(np.float32) - background, axis=2)
    # LAB difference supports both dark and light backgrounds; saturation provides
    # an additional clue when onions are placed on a neutral background.
    border_s = np.concatenate((hsv[0, :, 1], hsv[-1, :, 1], hsv[:, 0, 1], hsv[:, -1, 1]))
    saturated = (hsv[:, :, 1].astype(float) > np.median(border_s) + 45) & (distance > 15)
    mask = ((distance > config.BACKGROUND_DISTANCE) | saturated).astype(np.uint8) * 255
    for polygon in marker_polygons:
        exclusion = np.zeros_like(mask)
        cv2.fillConvexPoly(exclusion, polygon, 255)
        exclusion = cv2.dilate(exclusion, np.ones((11, 11), np.uint8))
        mask[exclusion > 0] = 0
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    candidates = []
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        if area < config.MIN_COMPONENT_AREA:
            continue
        if x == 0 or y == 0 or x + w >= mask.shape[1] or y + h >= mask.shape[0]:
            continue  # Partial objects at the image edge cannot be measured reliably.
        component = (labels == index).astype(np.uint8) * 255
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour = max(contours, key=cv2.contourArea)
        hull_area = cv2.contourArea(cv2.convexHull(contour))
        if min(w, h) / max(w, h) < 0.25 or cv2.contourArea(contour) / max(hull_area, 1) < 0.45:
            continue
        candidates.append({"bbox": [int(x), int(y), int(w), int(h)], "contour": contour})
    return sorted(candidates, key=lambda c: (c["bbox"][1], c["bbox"][0])), mask
