"""Import only known, hash-verified files from an existing extracted asset folder."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def validated_files(source, manifest):
    """Validate everything before copying anything; never import saves or extra files."""
    source = Path(source).resolve()
    result = []
    for name, expected in manifest.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'Unsafe manifest path: {name}')
        file = (source / relative).resolve()
        if not file.is_relative_to(source):
            raise ValueError(f'Asset escapes source directory: {name}')
        if not file.is_file():
            raise ValueError(f'Missing asset: {name}')
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Unsupported or damaged asset: {name}')
        result.append((file, relative))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Directory containing the extracted assets')
    parser.add_argument('--check', action='store_true', help='Verify without copying')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'assets/manifest.json').read_text())
    try:
        files = validated_files(args.source, manifest)
        if not args.check:
            for source, relative in files:
                target = ROOT / 'assets' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if source != target.resolve():
                    shutil.copyfile(source, target)
        print(f'{"Verified" if args.check else "Imported"} {len(files)} supported assets.')
    except (OSError, ValueError) as error:
        parser.exit(1, f'Asset import failed: {error}\n')


if __name__ == '__main__':
    main()
