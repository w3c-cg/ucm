"""
Utility functions for the ucm-codegen toolchain
"""

import re
from pathlib import Path
from typing import Any, Dict


def load_yaml_safe(path: Path) -> Dict[str, Any]:
    """Safely load YAML file"""
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def local_name(uri: str) -> str:
    """Extract local name from URI (after '#', '/', or a URN ':')"""
    for separator in ("#", "/", ":"):
        tail = uri.rsplit(separator, 1)[-1]
        if separator in uri and tail:
            return tail
    return uri


def kebab(term: str) -> str:
    """CareTrajectoryContext -> care-trajectory-context"""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", term).lower()


# Irregular plurals that show up in UCM class names
_IRREGULAR = {"criteria": "criteria", "focus": "foci", "person": "people", "datum": "data"}


def pluralize(word: str) -> str:
    lower = word.lower()
    if lower in _IRREGULAR:
        return _IRREGULAR[lower]
    if re.search(r"(s|x|z|ch|sh)$", lower):
        return word + "es"
    if re.search(r"[^aeiou]y$", lower):
        return word[:-1] + "ies"
    return word + "s"


def collection_segment(term: str) -> str:
    """Path segment for a resource: SemanticContext -> semantic-contexts"""
    *head, last = kebab(term).split("-")
    return "-".join(head + [pluralize(last)])


def pascal(segment: str) -> str:
    """semantic-contexts -> SemanticContexts"""
    return "".join(part[:1].upper() + part[1:] for part in segment.split("-"))


def article(phrase: str) -> str:
    return "an" if phrase[:1].lower() in "aeiou" else "a"
