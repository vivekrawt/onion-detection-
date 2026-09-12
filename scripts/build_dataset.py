"""Package Piyu12 annotations into mixed, reproducible YOLO dataset splits."""
import argparse
import hashlib
import json
import random
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLITS = {'train': 0.8, 'validate': 0.1, 'test': 0.1}


class UnionFind:
    def __init__(self):
        self.parents = {}

    def find(self, item):
        self.parents.setdefault(item, item)
        if self.parents[item] != item:
            self.parents[item] = self.find(self.parents[item])
        return self.parents[item]

    def union(self, a, b):
        self.parents[self.find(a)] = self.find(b)


def check_label(text, class_id):
    lines = text.strip().splitlines()
    if not lines:
        raise ValueError('Empty training label')
    for line in lines:
        fields = line.split()
        if len(fields) != 5 or fields[0] != str(class_id):
            raise ValueError(f'Incorrect class/label: {line}')
        x, y, w, h = map(float, fields[1:])
        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
            raise ValueError(f'Invalid coordinates: {line}')
        if min(x-w/2, y-h/2) < -0.000002 or max(x+w/2, y+h/2) > 1.000002:
            raise ValueError(f'Box outside image: {line}')
    return len(lines)


def allocate(groups, seed=42):
    """Greedy stratification by health class while preserving whole groups."""
    rng = random.Random(seed)
    ordered = list(groups.items())
    rng.shuffle(ordered)
    ordered.sort(key=lambda kv: len(kv[1]), reverse=True)
    totals = Counter(r['class_id'] for _, rows in ordered for r in rows)
    counts = {s: Counter() for s in SPLITS}
    assignments = {}
    for group, rows in ordered:
        added = Counter(r['class_id'] for r in rows)
        def cost(split):
            return sum(
                ((counts[s][c]+(added[c] if s == split else 0)-ratio*totals[c])**2)/max(1,ratio*totals[c])
                for s, ratio in SPLITS.items() for c in totals
            )
        best = min(SPLITS, key=cost)
        counts[best].update(added)
        assignments[group] = best
    return assignments


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--annotations', type=Path, default=ROOT/'data'/'annotations-piyu12-gpu-full')
    p.add_argument('--output', type=Path, default=ROOT/'onion-dataset')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--block-size', type=int, default=100)
    args = p.parse_args()
    if args.block_size < 1:
        p.error('block-size must be positive')
    inventory = json.loads((args.annotations/'inventory.json').read_text())
    records = [json.loads(f.read_text()) for f in sorted((args.annotations/'records').glob('*.json'))]
    if len(records) != inventory['total_images']:
        raise ValueError(f'Annotation incomplete: {len(records)} of {inventory["total_images"]}')
    if args.output.exists():
        raise ValueError('Destination exists; choose a new output to avoid overwriting a dataset')
    folders = defaultdict(list)
    for r in records:
        folders[str(Path(r['relative_path']).parent)].append(r)
    uf = UnionFind()
    hashes = defaultdict(list)
    for folder, rows in folders.items():
        def numeric(r):
            match = re.search(r'(\d+)$', Path(r['relative_path']).stem)
            return int(match.group(1)) if match else r['relative_path']
        for i, r in enumerate(sorted(rows, key=numeric)):
            r['sequence_block'] = f'{folder}::block-{i//args.block_size:05d}'
            uf.find(r['sequence_block'])
            r['sha256'] = hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()
            hashes[r['sha256']].append(r)
    conflict_hashes = {sha for sha, rows in hashes.items() if len({r['class_id'] for r in rows}) > 1}
    for rows in hashes.values():
        for r in rows[1:]:
            uf.union(rows[0]['sequence_block'], r['sequence_block'])
    groups = defaultdict(list)
    for r in records:
        r['group_id'] = uf.find(r['sequence_block'])
        if r['sha256'] in conflict_hashes:
            r['exclusion_reason'] = 'duplicate_with_conflicting_health_labels'
        elif not r['boxes'] or not r.get('label'):
            r['exclusion_reason'] = r['status']
        else:
            r['box_count'] = check_label(Path(r['label']).read_text(), r['class_id'])
            groups[r['group_id']].append(r)
    assignments = allocate(groups, args.seed)
    out = args.output.resolve()
    for split in SPLITS:
        for sub in ['images', 'labels']:
            (out/split/sub).mkdir(parents=True)
    (out/'review'/'images').mkdir(parents=True)
    counts = {s: {'images': 0, 'boxes': 0, 'healthy_images': 0, 'unhealthy_images': 0} for s in SPLITS}
    excluded = Counter()
    manifest = []
    for i, r in enumerate(records):
        key = hashlib.sha256(r['relative_path'].encode()).hexdigest()[:20]
        image_name = key+Path(r['source']).suffix.lower()
        item = {k:r[k] for k in ['relative_path','class_id','class_name','sha256','group_id']}
        if 'exclusion_reason' in r:
            item.update(split='review', reason=r['exclusion_reason'], image=f'review/images/{image_name}')
            excluded[r['exclusion_reason']] += 1
        else:
            split = assignments[r['group_id']]
            item.update(split=split, image=f'{split}/images/{image_name}', label=f'{split}/labels/{key}.txt', boxes=r['box_count'])
            shutil.copy2(r['label'], out/item['label'])
            counts[split]['images'] += 1
            counts[split]['boxes'] += r['box_count']
            counts[split][r['class_name']+'_images'] += 1
        shutil.copy2(r['source'], out/item['image'])
        manifest.append(item)
        if i % 1000 == 0:
            print(f'Packaged {i+1}/{len(records)}', flush=True)
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2))
    (out/'data.yaml').write_text(f'path: {json.dumps(out.as_posix())}\ntrain: train/images\nval: validate/images\ntest: test/images\nnc: 2\nnames:\n  0: healthy\n  1: unhealthy\n')
    report = {'input_images':len(records),'included_images':sum(v['images'] for v in counts.values()),'splits':counts,'review_images':sum(excluded.values()),'review_reasons':dict(excluded),'seed':args.seed,'target_ratios':SPLITS,'sequence_block_size':args.block_size,'exact_duplicate_groups':sum(len(v)>1 for v in hashes.values()),'annotation_settings':json.loads((args.annotations/'run.json').read_text())}
    (out/'summary.json').write_text(json.dumps(report,indent=2))
    (out/'README.md').write_text('# Mixed onion detection dataset\n\nClasses: 0 healthy, 1 unhealthy. Colors are combined. Labels are Piyu12-generated boxes with health inherited from source folders, accepted by the user as candidate annotations. They have not been manually corrected.\n\nTrain/validate/test target 80/10/10 with seed 42. Consecutive blocks of 100 numbered images within each source folder stay together; exact duplicate file hashes are also kept in one split. This is a heuristic grouping, not verified physical-onion/session independence. Similar views may still cross block boundaries. Validation/test labels come from the same teacher model and are not independent ground truth; manually review them before reporting model accuracy.\n\nImages with no detections or conflicting duplicate health labels are in review/images, excluded from the training YAML. They intentionally have no empty background labels. manifest.json preserves every source mapping and exclusion reason. data.yaml has the current absolute path; update it if moving the dataset. No augmentations were generated.\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__ == '__main__':
    main()
