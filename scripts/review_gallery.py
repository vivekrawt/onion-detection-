"""Build a local contact-sheet report of candidate annotations."""
import argparse
import html
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args = parser.parse_args()
    cards=[]
    for path in sorted((args.output/'records').glob('*.json')):
        r=json.loads(path.read_text())
        preview=Path(r['preview']).relative_to(args.output.resolve()).as_posix() if 'preview' in r else ''
        cards.append(f'<article><img loading="lazy" src="{html.escape(preview)}"><p>{html.escape(r["relative_path"])}</p><b>{r["class_name"]} · {len(r["boxes"])} boxes</b><p>{r["status"]}</p></article>')
    (args.output/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Onion annotation review</title><style>body{font:16px system-ui;background:#f4f5f1;padding:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:20px}article{background:white;padding:12px;border-radius:8px}img{width:100%}p{overflow-wrap:anywhere}</style><h1>Candidate onion annotations</h1><p>Folder labels: healthy / unhealthy. Inspect every bulb for missing, duplicate or merged boxes. These are unverified pseudo-labels.</p><main>'+''.join(cards)+'</main>',encoding='utf-8')
    print(args.output/'review.html')

if __name__=='__main__':
    main()
