"""Package nonempty candidate labels with image copies; no implied human approval."""
import argparse
import json
import shutil
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('annotations',type=Path)
    p.add_argument('destination',type=Path)
    args=p.parse_args()
    args.destination.mkdir(parents=True,exist_ok=False)
    for name in ['images','labels']:
        (args.destination/name).mkdir()
    manifest=[]
    for path in sorted((args.annotations/'records').glob('*.json')):
        r=json.loads(path.read_text())
        if not r.get('label') or not r['boxes']:
            continue
        stem=path.stem
        source=Path(r['source'])
        shutil.copy2(source,args.destination/'images'/(stem+source.suffix.lower()))
        shutil.copy2(r['label'],args.destination/'labels'/(stem+'.txt'))
        manifest.append({'id':stem,'source':r['source'],'status':r['status'],'boxes':len(r['boxes'])})
    (args.destination/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (args.destination/'classes.yaml').write_text('names:\n  0: healthy\n  1: unhealthy\n')
    (args.destination/'README.txt').write_text('UNVERIFIED CANDIDATE ANNOTATIONS. Correct missing/incorrect boxes before training. No-detection images were excluded, not treated as negatives. No train/validation split has been assigned. Preserve physical-onion/session groups when splitting. Class IDs: 0 healthy, 1 unhealthy.\n')
    print(f'Packaged {len(manifest)} candidate image/label pairs.')

if __name__=='__main__':
    main()
