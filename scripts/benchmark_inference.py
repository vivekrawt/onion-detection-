import os
import time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(root/'.cache'/'ultralytics')
import torch
from ultralytics import YOLO
import cv2
model=YOLO(str(root/'models'/'pretrained'/'piyu12-fruit-veg-yolo11m.pt'))
sample=next((root/'Red and White Onion Dataset'/'New Onion'/'Bulb'/'Healthy'/'Mixed'/'5WO5RO').glob('*.jpg'))
image=cv2.imread(str(sample))
model.predict(image,verbose=False,device='cpu')
for n in [1,2,4]:
    torch.set_num_threads(n)
    start=time.perf_counter()
    for _ in range(3):
        model.predict(image,verbose=False,device='cpu')
    print(f'{n} threads: {(time.perf_counter()-start)/3:.3f} seconds/image',flush=True)
