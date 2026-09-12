import os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(root/'.cache'/'ultralytics')
os.environ['YOLO_AUTOINSTALL']='false'
from ultralytics import YOLO
import openvino as ov
print('Available devices:',ov.Core().available_devices,flush=True)
model=YOLO(str(root/'models'/'pretrained'/'piyu12-fruit-veg-yolo11m.pt'))
model.export(format='openvino',imgsz=640,half=False,dynamic=False,batch=1,device='cpu')
