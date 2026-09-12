"""Compare original and accelerated Piyu12 pilot boxes."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union else 0

def main():
    original=ROOT/'data'/'annotations-pilot-piyu12-square'/'records'
    accelerated=ROOT/'data'/'annotations-pilot-piyu12-openvino'/'records'
    matches=[]
    differences=[]
    for f in sorted(original.glob('*.json')):
        a=json.loads(f.read_text())
        b=json.loads((accelerated/f.name).read_text())
        if len(a['boxes'])!=len(b['boxes']):
            differences.append({'image':a['relative_path'],'original':len(a['boxes']),'accelerated':len(b['boxes'])})
        remaining=list(b['boxes'])
        for box in a['boxes']:
            if remaining:
                best=max(range(len(remaining)),key=lambda i:iou(box['xyxy'],remaining[i]['xyxy']))
                matches.append(iou(box['xyxy'],remaining.pop(best)['xyxy']))
            else:
                matches.append(0)
    report={'images_compared':len(list(original.glob('*.json'))),'count_differences':differences,'original_boxes':len(matches),'minimum_matched_iou':min(matches),'mean_matched_iou':sum(matches)/len(matches)}
    (ROOT/'models'/'pretrained'/'acceleration-comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
