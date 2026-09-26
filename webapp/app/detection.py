"""Conservative consolidation of repeated views of the same visible bulb.

IoU alone misses a large group box containing several smaller onion boxes.
Remove those group boxes before suppressing duplicates. Adjacent overlapping
bulbs with distinct centers must remain separate.
"""
import math


def area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def overlap(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return intersection / max(area(a) + area(b) - intersection, 1e-9), intersection / max(min(area(a), area(b)), 1e-9)


def same_bulb(a, b):
    iou, contained = overlap(a, b)
    ax, ay = (a[0]+a[2])/2, (a[1]+a[3])/2
    bx, by = (b[0]+b[2])/2, (b[1]+b[3])/2
    distance = math.hypot(ax-bx, ay-by)
    return iou >= .45 or (contained >= .88 and distance < .28 * math.sqrt(max(area(a), area(b))))


def consolidate(detections, confidence=.25):
    boxes = [dict(d) for d in detections if d['confidence'] >= confidence and area(d['box']) > 0]
    groups = set()
    for i, outer in enumerate(boxes):
        children = []
        a = outer['box']
        for j, inner in enumerate(boxes):
            b = inner['box']
            cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2
            if i == j or area(b) > .65 * area(a) or inner['confidence'] < confidence:
                continue
            if a[0] <= cx <= a[2] and a[1] <= cy <= a[3] and overlap(a, b)[1] >= .85:
                if all(not same_bulb(b, child) for child in children):
                    children.append(b)
        if len(children) >= 2:
            groups.add(i)
    ordered = sorted((b for i,b in enumerate(boxes) if i not in groups), key=lambda b: -b['confidence'])
    kept = []
    for detection in ordered:
        duplicate = next((k for k in kept if same_bulb(k['box'], detection['box'])), None)
        if duplicate is None:
            detection['support'] = [detection.get('pass', 'single')]
            kept.append(detection)
        elif detection.get('pass', 'single') not in duplicate['support']:
            duplicate['support'].append(detection.get('pass', 'single'))
    kept.sort(key=lambda d: ((d['box'][1]+d['box'][3])/2, (d['box'][0]+d['box'][2])/2))
    for number, detection in enumerate(kept, 1):
        detection['id'] = number
    return kept, {'raw_candidates': len(boxes), 'group_boxes_removed': len(groups),
                  'duplicates_removed': len(ordered)-len(kept), 'visible_count': len(kept)}
