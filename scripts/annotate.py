"""Local onion pseudo-labeling. Folder names determine health, never model classes."""
import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
(ROOT / '.cache' / 'ultralytics').mkdir(parents=True, exist_ok=True)
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.cache' / 'ultralytics'))
os.environ.setdefault('TORCH_HOME', str(ROOT / '.cache' / 'torch'))
CLASSES = {'healthy': 0, 'unhealthy': 1}


def inventory(root):
    items = []
    for p in sorted(root.rglob('*')):
        if p.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}:
            continue
        rel = p.relative_to(root)
        labels = [part.lower() for part in rel.parts[:-1] if part.lower() in CLASSES]
        if len(labels) != 1:
            raise ValueError(f'Ambiguous/missing health folder: {rel}')
        items.append((p, rel, CLASSES[labels[0]]))
    if not items:
        raise ValueError(f'No images found in {root}')
    return items


def normalized_box(box, width, height):
    import math
    if not all(math.isfinite(float(v)) for v in box):
        return None
    x1, y1, x2, y2 = box
    x1, x2 = max(0, min(width, x1)), max(0, min(width, x2))
    y1, y2 = max(0, min(height, y1)), max(0, min(height, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return [(x1+x2)/2/width, (y1+y2)/2/height, (x2-x1)/width, (y2-y1)/height]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'Red and White Onion Dataset'/'New Onion'/'Bulb')
    parser.add_argument('--output', type=Path, default=ROOT/'data'/'annotations')
    parser.add_argument('--model', default=str(ROOT/'models'/'pretrained'/'onion-world.pt'))
    parser.add_argument('--inventory-only', action='store_true')
    parser.add_argument('--per-folder', type=int, default=0, help='Evenly spaced pilot samples per leaf folder; 0 = all')
    parser.add_argument('--confidence', type=float, default=0.20)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--no-previews', action='store_true', help='Skip preview JPEGs for bulk runs')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--square', action='store_true', help='Fixed square padding for exported models')
    parser.add_argument('--batch', type=int, default=1)
    args = parser.parse_args()
    if not 0 < args.confidence <= 1 or args.per_folder < 0 or args.batch < 1:
        parser.error('Invalid confidence or per-folder limit')
    items = inventory(args.source.resolve())
    counts = Counter(str(r.parent) for _, r, _ in items)
    summary = {'total_images': len(items), 'classes': dict(Counter('healthy' if c == 0 else 'unhealthy' for _, _, c in items)), 'folders': dict(counts)}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'inventory.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)
    if args.inventory_only:
        return
    if args.per_folder:
        groups = defaultdict(list)
        for item in items:
            groups[item[1].parent].append(item)
        items = [g[i] for g in groups.values() for i in sorted({round(j*(len(g)-1)/max(1,min(args.per_folder,len(g))-1)) for j in range(min(args.per_folder,len(g)))})]
    import cv2
    import numpy as np
    import torch
    torch.set_num_threads(args.threads)
    from ultralytics import YOLO
    model = YOLO(args.model, task='detect')
    model_path = Path(args.model)
    if model_path.is_dir() and (model_path/'metadata.yaml').exists():
        import yaml
        names = yaml.safe_load((model_path/'metadata.yaml').read_text())['names']
    else:
        names = model.names
    onion_ids = [i for i, n in names.items() if n.lower() in {'onion', 'onions', 'onion bulb'}]
    if not onion_ids:
        raise ValueError(f'Model has no onion class: {model.names}. Use prepare_model.py or onion detector weights.')
    model_hash = hashlib.sha256()
    if model_path.is_dir():
        for part in sorted(model_path.rglob('*')):
            if part.is_file():
                model_hash.update(str(part.relative_to(model_path)).encode())
                model_hash.update(part.read_bytes())
    else:
        model_hash.update(model_path.read_bytes())
    config = {'model_sha256': model_hash.hexdigest(), 'confidence': args.confidence, 'imgsz': args.imgsz, 'source': str(args.source.resolve()), 'classes': CLASSES}
    if args.square:
        config['square_padding'] = True
    if args.batch > 1:
        config['batch'] = args.batch
    config_path = args.output/'run.json'
    if config_path.exists() and json.loads(config_path.read_text()) != config:
        raise ValueError('Output belongs to different settings. Choose another --output folder.')
    config_path.write_text(json.dumps(config, indent=2))
    prediction_cache = {}
    for index, (path, rel, class_id) in enumerate(items):
        key = hashlib.sha256(str(rel).encode()).hexdigest()[:20]
        record_path = args.output/'records'/f'{key}.json'
        if record_path.exists():
            continue
        record_path.parent.mkdir(exist_ok=True)
        record = {'source': str(path), 'relative_path': str(rel), 'class_id': class_id, 'class_name': ['healthy','unhealthy'][class_id], 'status': 'needs_review', 'boxes': []}
        frame = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            record['status'] = 'decode_error'
        else:
            h, w = frame.shape[:2]
            record.update(width=w, height=h)
            if index not in prediction_cache:
                prediction_cache.clear()
                batch_items = items[index:index+args.batch]
                frames = [frame]
                for batch_path, _, _ in batch_items[1:]:
                    other = cv2.imdecode(np.fromfile(str(batch_path), dtype=np.uint8), cv2.IMREAD_COLOR)
                    frames.append(other if other is not None else np.zeros_like(frame))
                # Fixed-batch exports need padding; padded results are discarded.
                frames += [frame] * (args.batch-len(frames))
                predictions = model.predict(frames, batch=args.batch, conf=args.confidence, iou=0.45, imgsz=args.imgsz, device=args.device, classes=onion_ids, agnostic_nms=True, rect=not args.square, verbose=False)
                prediction_cache.update({index+offset:r for offset,r in enumerate(predictions[:len(batch_items)])})
            result = prediction_cache.pop(index)
            # Ultralytics resets CPU threads during first predictor setup.
            if torch.get_num_threads() != args.threads:
                torch.set_num_threads(args.threads)
            lines = []
            for box, score in zip(result.boxes.xyxy.cpu().tolist(), result.boxes.conf.cpu().tolist()):
                norm = normalized_box(box, w, h)
                if norm is None:
                    continue
                lines.append(str(class_id)+' '+' '.join(f'{n:.6f}' for n in norm))
                record['boxes'].append({'xyxy': box, 'confidence': score, 'yolo': norm})
                x1,y1,x2,y2 = map(int,box)
                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,200,0) if class_id == 0 else (0,80,255),2)
                cv2.putText(frame,f'{record["class_name"]} {score:.2f}',(x1,max(15,y1)),cv2.FONT_HERSHEY_SIMPLEX,0.45,(255,255,255),1)
            if not lines:
                record['status'] = 'no_detection'
            else:
                label = args.output/'labels'/rel.with_suffix('.txt')
                label.parent.mkdir(parents=True,exist_ok=True)
                label.write_text('\n'.join(lines)+'\n')
                record['label'] = str(label.resolve())
            if not args.no_previews:
                preview = args.output/'previews'/f'{key}.jpg'
                preview.parent.mkdir(exist_ok=True)
                scale = min(1, 960/w)
                cv2.imwrite(str(preview), cv2.resize(frame,(int(w*scale),int(h*scale))))
                record['preview'] = str(preview.resolve())
        temp = record_path.with_suffix('.tmp')
        temp.write_text(json.dumps(record,indent=2),encoding='utf-8')
        temp.replace(record_path)
        if index % 25 == 0:
            print(f'{index+1}/{len(items)} images processed',flush=True)
    records = [json.loads(p.read_text()) for p in (args.output/'records').glob('*.json')]
    result_summary = {'images':len(records),'boxes':sum(len(r['boxes']) for r in records),'statuses':dict(Counter(r['status'] for r in records))}
    (args.output/'summary.json').write_text(json.dumps(result_summary,indent=2))
    print(json.dumps(result_summary),flush=True)


if __name__ == '__main__':
    main()
