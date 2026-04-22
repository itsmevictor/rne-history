#!/usr/bin/env python3.11
"""Sync the Répertoire national des élus CSVs from data.gouv.fr.

Compares the sha1 of each resource reported by the data.gouv.fr API
to the sha1 of the local file; downloads and overwrites only when they
differ, and verifies the downloaded bytes against the expected sha1
before writing to disk.

Exits 0 on success (even if nothing changed) and 1 on any error.
Writes a short summary to stdout that the GitHub Actions workflow
uses as the commit message.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DATASET_URL = "https://www.data.gouv.fr/api/1/datasets/repertoire-national-des-elus-1/"
REPO_ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "rne-history-sync (+https://github.com)"
TIMEOUT = 120


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def sha1_of_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha1_of_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def main() -> int:
    try:
        meta = json.loads(http_get(DATASET_URL))
    except Exception as e:
        print(f"ERROR: failed to fetch dataset metadata: {e}", file=sys.stderr)
        return 1

    resources = [r for r in meta.get("resources", []) if r.get("type") == "main"]
    if not resources:
        print("ERROR: no 'main' resources found in API response", file=sys.stderr)
        return 1

    changed: list[str] = []
    added: list[str] = []
    unchanged: list[str] = []
    failed: list[str] = []

    for r in resources:
        filename = os.path.basename(urlparse(r["url"]).path)
        if not filename:
            failed.append(f"<no filename for resource {r.get('id')}>")
            continue

        expected_sha1 = (r.get("checksum") or {}).get("value")
        if not expected_sha1:
            failed.append(f"{filename} (no sha1 in API)")
            continue

        target = REPO_ROOT / filename
        local_sha1 = sha1_of_file(target) if target.exists() else None

        if local_sha1 == expected_sha1:
            unchanged.append(filename)
            continue

        # Use the stable URL so we hit the current version, not a cached one.
        download_url = r.get("latest") or r["url"]
        try:
            data = http_get(download_url)
        except Exception as e:
            failed.append(f"{filename} (download: {e})")
            continue

        actual_sha1 = sha1_of_bytes(data)
        if actual_sha1 != expected_sha1:
            failed.append(
                f"{filename} (sha1 mismatch: got {actual_sha1}, expected {expected_sha1})"
            )
            continue

        target.write_bytes(data)
        (added if local_sha1 is None else changed).append(filename)

    # Human summary on stderr, machine-readable lines on stdout for the workflow.
    print(
        f"RNE sync: {len(changed)} changed, {len(added)} added, "
        f"{len(unchanged)} unchanged, {len(failed)} failed",
        file=sys.stderr,
    )
    for label, items in [
        ("changed", changed),
        ("added", added),
        ("failed", failed),
    ]:
        for name in items:
            print(f"{label}: {name}", file=sys.stderr)

    # stdout: one line per file that moved, so the workflow can parse it.
    for name in changed:
        print(f"CHANGED\t{name}")
    for name in added:
        print(f"ADDED\t{name}")
    for name in failed:
        print(f"FAILED\t{name}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
