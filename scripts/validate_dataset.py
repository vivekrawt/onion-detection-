"""Verify every image/label pair, split grouping, hashes, and source coverage."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from build_dataset import check_label

def main():
    p=argparse.ArgumentParser()
    p.add_argument('dataset',type=Path)
    args=p.parse_args()
    root=args.dataset
    manifest=json.loads((root/'manifest.json').read_text())
    summary=json.loads((root/'summary.json').read_text())
    import yaml
    config=yaml.safe_load((root/'data.yaml').read_text())
    assert Path(config['path']).resolve()==root.resolve()
    assert config['names']=={0:'healthy',1:'unhealthy'}
    assert config['nc']==2
    assert {key:config[key] for key in ['train','val','test']}=={'train':'train/images','val':'validate/images','test':'test/images'}
    assert len(manifest)==summary['input_images']
    assert len({r['relative_path'] for r in manifest})==len(manifest)
    hashes=defaultdict(set)
    groups=defaultdict(set)
    counts=defaultdict(int)
    for r in manifest:
        path=root/r['image']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256'],str(path)
        if r['split']=='review':
            continue
        assert check_label((root/r['label']).read_text(),r['class_id'])==r['boxes']
        assert path.stem==Path(r['label']).stem
        hashes[r['sha256']].add(r['split'])
        groups[r['group_id']].add(r['split'])
        counts[r['split']]+=1
    assert all(len(s)==1 for s in hashes.values()),'Exact duplicate leakage'
    assert all(len(s)==1 for s in groups.values()),'Sequence-block leakage'
    assert len(list((root/'review'/'images').iterdir()))==summary['review_images']
    for split in ['train','validate','test']:
        images={p.stem for p in (root/split/'images').iterdir()}
        labels={p.stem for p in (root/split/'labels').iterdir()}
        assert images==labels
        assert len(images)==counts[split]==summary['splits'][split]['images']
        assert summary['splits'][split]['healthy_images']>0
        assert summary['splits'][split]['unhealthy_images']>0
    result={'passed':True,'source_images':len(manifest),'paired_images':sum(counts.values()),'splits':dict(counts),'checks':['source hashes','unique source coverage','YOLO coordinates and class IDs','paired filenames','no exact-duplicate or sequence-block split leakage','both health classes in each split']}
    (root/'validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
