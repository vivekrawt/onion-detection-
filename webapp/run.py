"""Start the Allium onion classification web app."""
import argparse
import sys
from pathlib import Path

# The shared CLIP package sits next to webapp, even when run from this folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1', help='Use 0.0.0.0 to allow other devices on your network')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    from app.main import app
    print(f'Allium is warming up the model, then serving at http://{"localhost" if args.host in {"127.0.0.1", "0.0.0.0"} else args.host}:{args.port}', flush=True)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
