"""Keep the full bulb and nearby shoots without CLIP's central square crop."""
import numpy as np
from PIL import Image


def square_pad(image):
    image = image.convert('RGB')
    # Constant neutral padding preserves shape and does not invent reflected shoots.
    side = max(image.size)
    padded = Image.new('RGB', (side, side), (127, 127, 127))
    padded.paste(image, ((side-image.width)//2, (side-image.height)//2))
    return padded


def onion_crop(rgb, candidates, index, fraction):
    x, y, w, h = candidates[index]['bbox']
    margin = max(8, int(max(w, h)*fraction))
    x0, y0 = max(0,x-margin), max(0,y-margin)
    x1, y1 = min(rgb.shape[1],x+w+margin), min(rgb.shape[0],y+h+margin)
    crop = rgb[y0:y1,x0:x1].copy()
    # Neutralize other detected bulbs outside the target rectangle. This avoids
    # borrowing a neighboring green shoot or rotten patch as evidence.
    target = np.zeros(crop.shape[:2], dtype=bool)
    target[y-y0:y+h-y0,x-x0:x+w-x0] = True
    for j, candidate in enumerate(candidates):
        if j == index:
            continue
        a,b,c,d = candidate['bbox']
        a0,b0 = max(0,a-x0),max(0,b-y0)
        a1,b1 = min(x1-x0,a+c-x0),min(y1-y0,b+d-y0)
        if a1>a0 and b1>b0:
            region=crop[b0:b1,a0:a1]
            region[~target[b0:b1,a0:a1]] = 127
    return Image.fromarray(crop)
