"""Approximate planar scale, valid only for a top-down controlled capture."""
import cv2
import numpy as np


def find_reference(rgb, config):
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY))
    polygons = [np.rint(c[0]).astype(np.int32) for c in corners]
    if ids is None:
        return None, polygons, "Reference marker not detected; physical size is unknown."
    matches = [i for i, marker_id in enumerate(ids.flatten()) if marker_id == config.REFERENCE_MARKER_ID]
    if len(matches) != 1:
        return None, polygons, "Exactly one configured reference marker is required; physical size is unknown."
    points = corners[matches[0]][0]
    sides = np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1)
    # Reject visibly skewed/tiny markers instead of providing misleading precision.
    if min(sides) < 15 or max(sides) / min(sides) > 1.20:
        return None, polygons, "Marker is too small or tilted; retake the image from above."
    return float(sides.mean() / config.REFERENCE_MARKER_SIZE_CM), polygons, None


def diameter_pixels(contour):
    # Minor dimension is less affected by a long stalk than enclosing-circle diameter.
    return float(min(cv2.minAreaRect(contour)[1]))
