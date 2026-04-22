# rne-history

Tracks the history of the **Répertoire national des élus** (RNE), the French
open dataset listing all elected officials, published on data.gouv.fr at
<https://www.data.gouv.fr/datasets/repertoire-national-des-elus-1>.

Each CSV at the root of this repo mirrors one resource of that dataset. The
files are overwritten in place when data.gouv.fr publishes a new version, so
past versions are recoverable via `git log` / `git show`.

## How it works

A daily GitHub Actions workflow (`.github/workflows/update-rne.yml`, cron at
06:00 UTC) runs `scripts/update_rne.py`, which:

1. Fetches the dataset metadata from the data.gouv.fr API.
2. For each `main` resource, compares the API's sha1 to the sha1 of the
   local file.
3. If they differ (or the file is missing), downloads from the resource's
   stable URL, verifies the downloaded sha1 matches the API's sha1, and
   overwrites the local file.
4. The workflow commits and pushes any resulting changes.

New resources appearing in the API are added automatically. Resources that
disappear from the API keep their last local copy — they're never deleted.

## Running locally

The script uses the Python 3.11 standard library only.

```sh
python3.11 scripts/update_rne.py
```

It prints one line per affected file on stdout (`CHANGED\t<name>`,
`ADDED\t<name>`, `FAILED\t<name>`) and a human summary on stderr.

## Source

- Dataset: <https://www.data.gouv.fr/datasets/repertoire-national-des-elus-1>
- API:     <https://www.data.gouv.fr/api/1/datasets/repertoire-national-des-elus-1/>
- License: the open license under which data.gouv.fr publishes the RNE.
