"""Summarize pilot coverage without calling it detection accuracy."""
import argparse
import json
from collections import Counter
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('directories',nargs='+',type=Path)
    args=p.parse_args()
    for directory in args.directories:
        records=[json.loads(f.read_text()) for f in (directory/'records').glob('*.json')]
        stats={}
        for cls in ['healthy','unhealthy']:
            subset=[r for r in records if r['class_name']==cls]
            stats[cls]={'images':len(subset),'images_with_boxes':sum(bool(r['boxes']) for r in subset),'boxes':sum(len(r['boxes']) for r in subset)}
        print(json.dumps({'directory':str(directory),'images':len(records),'statuses':dict(Counter(r['status'] for r in records)),'classes':stats},indent=2))

if __name__=='__main__':
    main()
