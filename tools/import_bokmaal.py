"""Build the offline index from local exports; never downloads anything."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'sandbox' / 'norwegian'))
from dictionary_help import build_index, cache_path

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--concepts', type=Path, required=True)
    p.add_argument('--output', type=Path, default=cache_path())
    args = p.parse_args()
    print(json.dumps(build_index(args.source, args.concepts, args.output), indent=2, ensure_ascii=True))
