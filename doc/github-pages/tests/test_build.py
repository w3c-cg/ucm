"""Listing criteria, rendering and the committed-pages check"""

import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
sys.path.insert(0, str(DOCS))

import build  # noqa: E402

TODAY = date(2026, 11, 3)
SAMPLE_SITE = HERE / "sample-workbench.yaml"
SAMPLE_ENTRIES = HERE / "sample-entries.yaml"

GOOD = {
    "name": "Example Care Platform",
    "url": "https://example.org/care-platform",
    "profile": "ucm-core",
    "test_run": "https://example.org/care-platform/runs/1",
    "license": "Apache-2.0",
    "reported": "2026-11-01",
}


@pytest.fixture
def site():
    return build.load_site(SAMPLE_SITE)


def entries_file(tmp_path, *entries):
    path = tmp_path / "entries.yaml"
    path.write_text(yaml.safe_dump({"entries": list(entries)}), encoding="utf-8")
    return path


def problems(tmp_path, site, *entries):
    with pytest.raises(build.EntryError) as caught:
        build.load_entries(entries_file(tmp_path, *entries), site, today=TODAY)
    return "\n".join(caught.value.problems)


# ============= Criteria =============

def test_committed_files_are_valid():
    site = build.load_site(DOCS / "workbench.yaml")
    build.load_entries(DOCS / "implementations" / "entries.yaml", site, today=TODAY)


def test_good_entry_is_listed(tmp_path, site):
    [entry] = build.load_entries(entries_file(tmp_path, GOOD), site, today=TODAY)
    assert entry.reported == date(2026, 11, 1)


@pytest.mark.parametrize("field", ["contact", "pricing", "support", "description"])
def test_only_the_listing_fields_are_accepted(tmp_path, site, field):
    assert f"{field}: Extra inputs are not permitted" in problems(tmp_path, site, {**GOOD, field: "x"})


@pytest.mark.parametrize("field", ["url", "test_run"])
@pytest.mark.parametrize("value", ["http://example.org/x", "ftp://example.org/x", "example.org", "https://user:pw@example.org/"])
def test_urls_must_be_public_https(tmp_path, site, field, value):
    assert f"{field}:" in problems(tmp_path, site, {**GOOD, field: value})


@pytest.mark.parametrize("name", [
    "Certified UCM Server", "UCM Standard Edition", "Endorsed Care Hub",
    "Official UCM Adapter", "W3C UCM Toolkit", "Conformant Care Router",
])
def test_names_carry_no_endorsement_language(tmp_path, site, name):
    assert "implies certification or endorsement" in problems(tmp_path, site, {**GOOD, "name": name})


def test_unknown_profile_is_rejected(tmp_path, site):
    assert "is not one of" in problems(tmp_path, site, {**GOOD, "profile": "food-access"})


@pytest.mark.parametrize("license", ["", "Apache 2.0 license!", "MIT, BSD"])
def test_license_must_be_spdx(tmp_path, site, license):
    assert "license:" in problems(tmp_path, site, {**GOOD, "license": license})


def test_spdx_expressions_are_accepted(tmp_path, site):
    for license in ["MIT OR Apache-2.0", "(GPL-2.0-only WITH Classpath-exception-2.0)", "LicenseRef-Proprietary"]:
        build.load_entries(entries_file(tmp_path, {**GOOD, "license": license}), site, today=TODAY)


def test_reported_date_is_not_in_the_future(tmp_path, site):
    assert "is in the future" in problems(tmp_path, site, {**GOOD, "reported": "2027-01-01"})


def test_duplicates_are_rejected(tmp_path, site):
    found = problems(tmp_path, site, GOOD, {**GOOD, "name": GOOD["name"].upper(), "url": "https://example.org/other"},
                     {**GOOD, "name": "Another"})
    assert "duplicates an earlier entry" in found
    assert "already listed as Example Care Platform" in found


def test_problems_name_the_entry(tmp_path, site):
    assert "entry 2 (Broken):" in problems(tmp_path, site, GOOD, {**GOOD, "name": "Broken", "url": "nope"})


# ============= Rendering =============

def render_samples():
    site = build.load_site(SAMPLE_SITE)
    return build.render(site, build.load_entries(SAMPLE_ENTRIES, site, today=TODAY))


def test_listing_is_alphabetical_not_file_order():
    page = render_samples()["implementations/index.html"]
    names = ["Discharge Handoff Kit (sample)", "sample care ledger", "Sample Referral Router"]  # case-insensitive
    positions = [page.index(f">{name}</a>") for name in names]
    assert positions == sorted(positions)


def test_page_carries_the_disclaimer_and_no_commercial_links():
    pages = render_samples()
    page = pages["implementations/index.html"]
    assert "W3C does not endorse specific products. The UCM Community Group does not endorse specific products." in page
    assert 'href="disclaimer.html"' in page
    assert "mailto:" not in page
    assert page.count('rel="nofollow external"') == 6
    assert "not a W3C Standard" in pages["implementations/disclaimer.html"]


def test_profile_filter_only_with_several_profiles(tmp_path):
    assert 'aria-label="Profile"' in render_samples()["implementations/index.html"]
    site = build.load_site(DOCS / "workbench.yaml")
    one = build.load_entries(entries_file(tmp_path, GOOD), site, today=TODAY)
    assert 'aria-label="Profile"' not in build.render(site, one)["implementations/index.html"]


def test_empty_listing_explains_how_to_submit():
    site = build.load_site(DOCS / "workbench.yaml")
    page = build.render(site, [])["implementations/index.html"]
    assert "No implementations reported yet" in page
    assert "implementations.js" not in page


def test_entry_text_is_escaped(tmp_path, site):
    [entry] = build.load_entries(entries_file(tmp_path, {**GOOD, "name": "Care <script>"}), site, today=TODAY)
    page = build.render(site, [entry])["implementations/index.html"]
    assert "Care &lt;script&gt;" in page and "Care <script>" not in page


def test_unbalanced_html_fails_rendering():
    with pytest.raises(ValueError, match="unexpected </div>"):
        build.check_html("x.html", "<main><p>text</div></main>")
    with pytest.raises(ValueError, match="unclosed"):
        build.check_html("x.html", "<main><section>")


def test_rendering_is_deterministic():
    assert render_samples() == render_samples()


# ============= Committed pages =============

def test_committed_pages_are_current():
    assert build.main(["--check"]) == 0


def test_check_reports_stale_pages(tmp_path, capsys):
    assert build.main(["--out", str(tmp_path), "--check"]) == 1
    assert "implementations/index.html" in capsys.readouterr().err
    assert build.main(["--out", str(tmp_path)]) == 0
    assert build.main(["--out", str(tmp_path), "--check"]) == 0


def test_invalid_entries_fail_the_build(tmp_path, capsys):
    path = entries_file(tmp_path, {**GOOD, "name": "Certified Thing"})
    assert build.main(["--entries", str(path), "--out", str(tmp_path)]) == 1
    assert "do not meet the listing criteria" in capsys.readouterr().err
    assert not (tmp_path / "implementations").exists()
