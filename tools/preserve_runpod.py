"""Stream one remote artifact into a verified-private GitHub draft release.

GitHub credentials stay in this local process. Large bytes flow SSH -> HTTPS
without a local temporary artifact. Never publishes releases or deletes assets.
"""
import argparse
import hashlib
import http.client
import json
from pathlib import Path
import shlex
import subprocess
import urllib.parse


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--remote-path', required=True)
    p.add_argument('--asset-name', required=True)
    p.add_argument('--repo', default='isaiahb/AstraFactory')
    p.add_argument('--tag', default='contact-learning-checkpoint-20260908')
    p.add_argument('--host', default='root@216.81.151.3')
    p.add_argument('--port', default='10715')
    p.add_argument('--key', default='/tmp/astrafactory-runpod/id_ed25519')
    p.add_argument('--known-hosts', default='/tmp/astrafactory-runpod/known_hosts')
    p.add_argument('--receipt-dir', default='/tmp/astrafactory-runpod/receipts')
    args = p.parse_args()
    token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, check=True).stdout.strip()
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'User-Agent': 'AstraFactory-ArtifactPreserver/1.0', 'X-GitHub-Api-Version': '2022-11-28'}

    def api(method, path, payload=None, host='api.github.com', content_type='application/json'):
        conn = http.client.HTTPSConnection(host, timeout=120)
        raw = None if payload is None else (payload if isinstance(payload, bytes) else json.dumps(payload).encode())
        conn.request(method, path, body=raw, headers={**headers, 'Content-Type': content_type})
        response = conn.getresponse()
        data = response.read()
        if response.status >= 300:
            raise RuntimeError(f'GitHub API HTTP {response.status}; response body withheld')
        return json.loads(data) if data else {}

    repo = api('GET', '/repos/' + args.repo)
    if not repo.get('private'):
        raise RuntimeError('Repository is not private; refusing upload')
    releases = api('GET', f'/repos/{args.repo}/releases?per_page=100')
    matches = [r for r in releases if r['tag_name'] == args.tag]
    if len(matches) > 1:
        raise RuntimeError('Ambiguous release tag')
    release = matches[0] if matches else api('POST', f'/repos/{args.repo}/releases', {
        'tag_name': args.tag, 'name': 'Private contact-learning artifacts — 2026-09-08',
        'draft': True, 'prerelease': True,
        'body': 'Private preservation of simulation demonstrations, learned-policy checkpoints and evidence. '
                'Draft only. Learned task success must be read from the paired evaluation reports; '
                'checkpoint existence alone does not establish successful insertion. '
                'Companion SHA256 files verify each archive. No physical robot validation is claimed.'})
    if not release['draft']:
        raise RuntimeError('Release is not a draft; refusing upload')
    ssh = ['ssh', '-i', args.key, '-p', args.port, '-o', 'UserKnownHostsFile=' + args.known_hosts,
           '-o', 'StrictHostKeyChecking=yes', args.host]
    remote = shlex.quote(args.remote_path)
    size = int(subprocess.run(ssh + ['stat -c %s -- ' + remote], capture_output=True, text=True, check=True).stdout)
    expected = subprocess.run(ssh + ['sha256sum -- ' + remote], capture_output=True, text=True, check=True).stdout.split()[0]
    if not 0 < size < 2 * 1024**3:
        raise ValueError('Artifact must be nonempty and smaller than 2 GiB')
    assets = api('GET', f'/repos/{args.repo}/releases/{release["id"]}/assets?per_page=100')
    if any(a['name'] == args.asset_name for a in assets):
        raise RuntimeError('Asset name already exists; refusing replacement or deletion')
    upload_path = f'/repos/{args.repo}/releases/{release["id"]}/assets?name=' + urllib.parse.quote(args.asset_name, safe='')
    conn = http.client.HTTPSConnection('uploads.github.com', timeout=120)
    conn.putrequest('POST', upload_path)
    for key, value in {**headers, 'Content-Type': 'application/octet-stream', 'Content-Length': str(size)}.items():
        conn.putheader(key, value)
    conn.endheaders()
    process = subprocess.Popen(ssh + ['cat -- ' + remote], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    digest, sent, report = hashlib.sha256(), 0, 0
    try:
        while chunk := process.stdout.read(1024 * 1024):
            conn.send(chunk)
            digest.update(chunk)
            sent += len(chunk)
            if sent - report >= 64 * 1024 * 1024:
                print(f'{args.asset_name}: {sent}/{size} bytes streamed', flush=True)
                report = sent
        if process.wait() or sent != size or digest.hexdigest() != expected:
            raise RuntimeError('SSH stream size or SHA256 mismatch')
        response = conn.getresponse()
        raw = response.read()
        if response.status != 201:
            raise RuntimeError(f'Asset upload HTTP {response.status}; response body withheld')
        asset = json.loads(raw)
    finally:
        if process.poll() is None:
            process.terminate()
        conn.close()
    if asset.get('size') != size:
        raise RuntimeError('GitHub asset size mismatch')
    if asset.get('digest') and asset['digest'] != 'sha256:' + expected:
        raise RuntimeError('GitHub asset digest mismatch')
    checksum = f'{expected}  {args.asset_name}\n'.encode()
    api('POST', f'/repos/{args.repo}/releases/{release["id"]}/assets?name=' +
        urllib.parse.quote(args.asset_name + '.sha256', safe=''), checksum,
        host='uploads.github.com', content_type='text/plain')
    receipt = {'repository': args.repo, 'private': True, 'draft': True, 'release_id': release['id'],
               'release_url': release['html_url'], 'asset_id': asset['id'], 'asset_name': asset['name'],
               'bytes': size, 'sha256': expected, 'github_digest': asset.get('digest'),
               'remote_source': args.remote_path, 'local_large_file_created': False}
    out = Path(args.receipt_dir)
    print(json.dumps(receipt), flush=True)
    try:
        out.mkdir(parents=True, exist_ok=True)
        (out / (args.asset_name + '.json')).write_text(json.dumps(receipt, indent=2))
    except OSError:
        print('Local receipt could not be saved; verified GitHub asset and SHA256 companion are preserved.', flush=True)


if __name__ == '__main__':
    main()
