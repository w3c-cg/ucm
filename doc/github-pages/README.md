# UCM workbench pages (draft)

Static pages for the group's site, starting with the implementations page
proposed in the adoption issue. Plain HTML, CSS and a little JavaScript,
built from YAML; the `pages` workflow deploys this folder to GitHub Pages
on every push to `main` that touches it. The page stays a draft until the
group and chairs adopt it.

| Path | What it is |
|---|---|
| `implementations/entries.yaml` | The listings. Submissions edit this file |
| `workbench.yaml` | Site settings and the profiles an entry may target. Chairs only |
| `implementations/index.html`, `disclaimer.html` | Generated pages, committed. Never edit by hand |
| `templates/`, `assets/` | Page templates; shared stylesheet (semantic tokens, light and dark) and filter script |
| `build.py` | Validates the entries and renders the pages |
| `tests/` | Tests, plus sample entries for previewing (`example.org` only, never published) |

## Submitting an implementation

Add one entry to `implementations/entries.yaml` and open a pull request:

```yaml
- name: Example Care Platform
  url: https://example.org/care-platform              # public project or repository
  profile: ucm-core                                   # an id from workbench.yaml
  test_run: https://example.org/care-platform/runs/42 # public run of the group's fixtures
  license: Apache-2.0                                 # SPDX identifier or expression
  reported: 2026-11-01                                # date the results were reported
```

An entry has exactly these fields. CI rejects an entry that:

- has any other field (contact, pricing, support and the like);
- uses a URL that is not public `https`, or that does not resolve;
- targets a profile that `workbench.yaml` does not define;
- has a license that is not an SPDX identifier or expression;
- has a reported-on date in the future;
- duplicates the name or URL of another entry;
- uses certification or endorsement language in its name (`certified`,
  `standard`, `endorsed`, `official`, `conformant`, `W3C` and similar; the
  list is `ENDORSEMENT` in `build.py`).

Test runs must use synthetic data only.

## Review

The chairs own the page and review every submission. A reviewer does not
review a submission they are involved in. CI checks the objective criteria;
review confirms that the test run is a run of the group's fixtures.

## Building

Python 3.10+ with `pip install -r doc/github-pages/requirements.txt`:

```bash
python doc/github-pages/build.py                 # validate and write the pages
python doc/github-pages/build.py --check         # validate; fail if committed pages are stale
python doc/github-pages/build.py --check-links   # also fetch every entry URL
pytest doc/github-pages/tests
```

Commit the regenerated pages with the entry. The `workbench` workflow runs
`--check --check-links` and the tests on every change under `doc/github-pages/`.

To preview with sample entries, render them somewhere outside the repository
and copy `assets/` next to the output:

```bash
python doc/github-pages/build.py --config doc/github-pages/tests/sample-workbench.yaml --entries doc/github-pages/tests/sample-entries.yaml --out <preview-dir>
```
