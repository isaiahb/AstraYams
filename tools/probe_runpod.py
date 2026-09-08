"""RunPod readiness probe with an explicitly selected task-stop watchdog.

Uses only RUNPOD_API_KEY, not the potentially stale runpodctl config key.
Explicit User-Agent avoids the observed urllib Cloudflare 1010 rejection.
Default mode is read-only. --watchdog-state may stop only the exact uniquely
named task Pod at its saved deadline or stop_now flag; never creates or resumes.
Only allowlisted account/Pod fields are printed; secrets and raw responses are not.
"""
import json
import os
import urllib.error
import urllib.request
import argparse
import datetime
import pathlib
import time


def request(url, payload=None, method=None):
    key = os.environ.get("RUNPOD_API_KEY")
    if not key:
        raise RuntimeError("RUNPOD_API_KEY is missing")
    req = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + key,
                 "User-Agent": "AstraFactory-ReadOnlyProbe/1.0",
                 "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"RunPod HTTP {error.code}; response body withheld") from None


def main():
    pods = request("https://rest.runpod.io/v1/pods")
    allowed = ("id", "name", "desiredStatus", "costPerHr", "imageName",
               "containerDiskInGb", "volumeInGb", "ports", "templateId")
    account = request("https://api.runpod.io/graphql", {
        "query": "query { myself { clientBalance currentSpendPerHr } }"})
    quotes = request("https://api.runpod.io/graphql", {"query": """
        query { gpuTypes { id displayName memoryInGb
          lowestPrice(input: {gpuCount: 1}) { uninterruptablePrice } } }
    """})
    selected = {"A100 PCIe", "A100 SXM", "RTX 4090", "A40", "RTX A6000"}
    print(json.dumps({
        "pods": [{k: p.get(k) for k in allowed} for p in pods],
        "account": account.get("data", {}).get("myself"),
        "gpu_quotes": [g for g in quotes.get("data", {}).get("gpuTypes", [])
                       if g["displayName"] in selected],
        "billing_actions": "none",
    }, indent=2))


def watchdog(state_path):
    state_path = pathlib.Path(state_path)
    ready = state_path.with_suffix('.watchdog-ready')
    ready.write_text(str(os.getpid()))
    while True:
        try:
            state = json.loads(state_path.read_text())
            pods = request('https://rest.runpod.io/v1/pods')
            targets = [p for p in pods if p.get('name') == state['name']]
            # Exact unique task name protects all pre-existing user resources.
            deadline = datetime.datetime.fromisoformat(state['deadline']).timestamp()
            should_stop = time.time() >= deadline or state.get('stop_now', False)
            if targets and all(p.get('desiredStatus') in ('EXITED', 'TERMINATED') for p in targets):
                print('Verified target stopped', flush=True)
                return
            if should_stop:
                for pod in targets:
                    request(f"https://rest.runpod.io/v1/pods/{pod['id']}/stop", {}, 'POST')
                print('Requested target stop; awaiting verification', flush=True)
        except Exception as error:
            print('Watchdog retry', type(error).__name__, flush=True)
        time.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--watchdog-state')
    args = parser.parse_args()
    if args.watchdog_state:
        watchdog(args.watchdog_state)
    else:
        main()
