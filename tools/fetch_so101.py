"""Fetch the official SO-101 description at an immutable upstream revision."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'eecbe3e0a9ebb23e25ad7b2759b03884c6660903'
REPO = 'TheRobotStudio/SO-ARM100'


def main():
    destination = ROOT / 'assets/robots/so101/upstream'
    tree = json.load(urllib.request.urlopen(
        f'https://api.github.com/repos/{REPO}/git/trees/{REVISION}?recursive=1'))['tree']
    prefix = 'Simulation/SO101/'
    paths = [x['path'] for x in tree if x['type'] == 'blob' and
             x['path'].startswith(prefix) and not x['path'].endswith('.part')]
    paths += ['LICENSE']
    def fetch(path):
        relative = path.removeprefix(prefix)
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        data = urllib.request.urlopen(
            f'https://raw.githubusercontent.com/{REPO}/{REVISION}/{path}', timeout=45).read()
        output.write_bytes(data)
        return dict(path=relative, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, paths))
    manifest = dict(repository=f'https://github.com/{REPO}', revision=REVISION,
                    license='Apache-2.0; see upstream/LICENSE', files=records,
                    modifications='None in upstream/. Workcell adaptations are generated separately.')
    (destination.parent / 'source.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(files=len(records), total_bytes=sum(x['bytes'] for x in records))))


if __name__ == '__main__':
    main()
