"""Download official YOLO-World weights and embed the onion prompt locally."""
import os
from pathlib import Path
root = Path(__file__).resolve().parents[1]
(root/'.cache'/'ultralytics').mkdir(parents=True, exist_ok=True)
os.environ['YOLO_CONFIG_DIR'] = str(root/'.cache'/'ultralytics')
os.environ['TORCH_HOME'] = str(root/'.cache'/'torch')
os.environ['YOLO_AUTOINSTALL'] = 'false'
from ultralytics import YOLOWorld
(root/'models'/'pretrained').mkdir(parents=True, exist_ok=True)
model = YOLOWorld(str(root/'models'/'pretrained'/'yolov8s-worldv2.pt'))
model.set_classes(['onion'])
model.save(str(root/'models'/'pretrained'/'onion-world.pt'))
print('Saved onion-prompt detector. This is not a trained health classifier.')
