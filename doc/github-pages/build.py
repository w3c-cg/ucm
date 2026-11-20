"""
Build the UCM workbench pages from YAML

  python doc/github-pages/build.py                 validate the entries and write the pages
  python doc/github-pages/build.py --check         validate; fail if the committed pages are stale
  python doc/github-pages/build.py --check-links   also fetch every entry URL (CI does this)

Entries are listed on objective criteria only: the fields are fixed (no
contact, pricing or support fields), every URL is public https, the profile
is one the group defines, and the name carries no endorsement language.
Pages are rendered alphabetically and without timestamps, so the same YAML
always produces the same bytes.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Annotated, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

DOCS = Path(__file__).resolve().parent
TEMPLATES = DOCS / "templates"

# Words a listing must not use: the group neither certifies nor endorses
ENDORSEMENT = re.compile(
    r"\b(certif\w*|endors\w*|standard\w*|official\w*|accredit\w*|approved|conformant|compliant|w3c)\b",
    re.IGNORECASE,
)
SPDX_TOKEN = re.compile(r"^[A-Za-z0-9.+-]+$")


# ============= Models =============

def _https(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("must be a public https URL")
    if parts.username or parts.password:
        raise ValueError("must not carry credentials")
    return value


def _spdx(value: str) -> str:
    tokens = value.replace("(", " ").replace(")", " ").split()
    if not tokens or not all(t in {"AND", "OR", "WITH"} or SPDX_TOKEN.match(t) for t in tokens):
        raise ValueError("must be an SPDX license identifier or expression, e.g. Apache-2.0")
    return value


HttpsUrl = Annotated[str, AfterValidator(_https)]
License = Annotated[str, AfterValidator(_spdx)]


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    title: str
    description: str


class Site(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    draft: bool = False
    repository: HttpsUrl
    group: HttpsUrl
    mailing_list: HttpsUrl
    profiles: List[Profile] = Field(min_length=1)


class Entry(BaseModel):
    """One listing. Exactly these fields: anything else is rejected."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)
    url: HttpsUrl = Field(description="Public project or repository")
    profile: str
    test_run: HttpsUrl = Field(description="Public run of the group's fixtures")
    license: License
    reported: date = Field(description="Date the results were reported")

    @property
    def host(self) -> str:
        return urlsplit(self.test_run).hostname or ""


class Entries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: List[Entry] = Field(default_factory=list)


# ============= Validation =============

class EntryError(Exception):
    def __init__(self, problems: List[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


def _pydantic_problems(error: ValidationError, raw: dict, label: str) -> List[str]:
    problems = []
    for item in error.errors():
        location = list(item["loc"])
        where = label
        if len(location) >= 2 and location[0] == "entries" and isinstance(location[1], int):
            index = location[1]
            entry = (raw.get("entries") or [])[index]
            name = entry.get("name") if isinstance(entry, dict) else None
            where = f"entry {index + 1}" + (f" ({name})" if name else "")
            location = location[2:]
        field = ".".join(str(part) for part in location) or "(entry)"
        problems.append(f"{where}: {field}: {item['msg']}")
    return problems


def load_site(path: Path) -> Site:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return Site.model_validate(raw)
    except ValidationError as e:
        raise EntryError(_pydantic_problems(e, raw, path.name)) from e


def load_entries(path: Path, site: Site, today: Optional[date] = None) -> List[Entry]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        entries = Entries.model_validate(raw).entries
    except ValidationError as e:
        raise EntryError(_pydantic_problems(e, raw, path.name)) from e

    today = today or date.today()
    profiles = {p.id for p in site.profiles}
    problems = []
    seen_names: Dict[str, str] = {}
    seen_urls: Dict[str, str] = {}
    for entry in entries:
        where = f"{entry.name}"
        if entry.profile not in profiles:
            problems.append(f"{where}: profile: '{entry.profile}' is not one of {', '.join(sorted(profiles))}")
        match = ENDORSEMENT.search(entry.name)
        if match:
            problems.append(f"{where}: name: '{match.group(0)}' implies certification or endorsement")
        if entry.reported > today:
            problems.append(f"{where}: reported: {entry.reported} is in the future")
        key = entry.name.casefold()
        if key in seen_names:
            problems.append(f"{where}: name: duplicates an earlier entry")
        seen_names[key] = entry.name
        if entry.url in seen_urls:
            problems.append(f"{where}: url: already listed as {seen_urls[entry.url]}")
        seen_urls[entry.url] = entry.name
    if problems:
        raise EntryError(problems)
    return entries


def check_links(entries: List[Entry], timeout: float = 20) -> List[str]:
    """Every listed URL must be publicly reachable (the listing criterion)"""
    problems = []
    for entry in entries:
        for field in ("url", "test_run"):
            url = getattr(entry, field)
            request = Request(url, headers={"User-Agent": "ucm-workbench-link-check"})
            try:
                with urlopen(request, timeout=timeout):
                    pass
            except HTTPError as e:
                problems.append(f"{entry.name}: {field}: {url} returned HTTP {e.code}")
            except (URLError, TimeoutError, OSError) as e:
                problems.append(f"{entry.name}: {field}: {url} is unreachable ({getattr(e, 'reason', e)})")
    return problems


# ============= Rendering =============

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _Balance(HTMLParser):
    """Rendered pages must parse: every non-void element closes, in order"""

    def __init__(self) -> None:
        super().__init__()
        self.stack: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            raise ValueError(f"unexpected </{tag}> (open: {' > '.join(self.stack) or 'nothing'})")
        self.stack.pop()


def check_html(name: str, text: str) -> None:
    parser = _Balance()
    try:
        parser.feed(text)
        parser.close()
    except ValueError as e:
        raise ValueError(f"{name}: {e}") from e
    if parser.stack:
        raise ValueError(f"{name}: unclosed {' > '.join(parser.stack)}")


def render(site: Site, entries: List[Entry]) -> Dict[str, str]:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    context = {
        "site": site,
        "entries": sorted(entries, key=lambda e: (e.name.casefold(), e.url)),
        "profiles": {p.id: p for p in site.profiles},
        "counts": Counter(e.profile for e in entries),
        "root": "../",
    }
    pages = {
        "implementations/index.html": env.get_template("implementations.html.j2").render(page="implementations", **context),
        "implementations/disclaimer.html": env.get_template("disclaimer.html.j2").render(page="disclaimer", **context),
    }
    for name, text in pages.items():
        check_html(name, text)
    return pages


def stale(pages: Dict[str, str], out: Path) -> List[str]:
    stale = []
    for name, text in pages.items():
        path = out / name
        current = path.read_bytes().replace(b"\r\n", b"\n") if path.exists() else None
        if current != text.encode("utf-8"):
            stale.append(name)
    return stale


def write(pages: Dict[str, str], out: Path) -> List[str]:
    written = stale(pages, out)
    for name in written:
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(pages[name], encoding="utf-8", newline="\n")
    return written


# ============= CLI =============

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--config", type=Path, default=DOCS / "workbench.yaml")
    parser.add_argument("--entries", type=Path, default=DOCS / "implementations" / "entries.yaml")
    parser.add_argument("--out", type=Path, default=DOCS)
    parser.add_argument("--check", action="store_true", help="Fail if the pages on disk are stale; write nothing")
    parser.add_argument("--check-links", action="store_true", help="Fetch every entry URL")
    args = parser.parse_args(argv)

    try:
        site = load_site(args.config)
        entries = load_entries(args.entries, site)
    except EntryError as e:
        print("Entries do not meet the listing criteria:", file=sys.stderr)
        for problem in e.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if args.check_links:
        problems = check_links(entries)
        if problems:
            print("Unreachable links:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1

    pages = render(site, entries)
    if args.check:
        outdated = stale(pages, args.out)
        if outdated:
            print("Pages are stale; run python doc/github-pages/build.py and commit:", file=sys.stderr)
            for name in outdated:
                print(f"  - {name}", file=sys.stderr)
            return 1
        print(f"{len(entries)} entries valid; pages are current")
        return 0

    written = write(pages, args.out)
    print(f"{len(entries)} entries valid; wrote {len(written)} of {len(pages)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
