import os
import shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(root/'.cache'/'ultralytics')
os.environ['YOLO_AUTOINSTALL']='false'
from ultralytics import YOLO
weights=root/'models'/'pretrained'/'piyu12-batch4.pt'
if not weights.exists():
    shutil.copy2(root/'models'/'pretrained'/'piyu12-fruit-veg-yolo11m.pt',weights)
YOLO(str(weights)).export(format='openvino',imgsz=640,quantize=None,dynamic=False,batch=4,device='cpu')
