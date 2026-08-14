"""Expand acronyms users say that the corpus does not use.

Deterministic lookup rather than LLM rewriting. It either matches or it
does not, so it cannot invent a visa type that does not exist. That matters
more here than breadth: a wrong-but-plausible expansion would retrieve real
clauses about the wrong pathway.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import get_settings


@dataclass(frozen=True)
class Acronym:
    term: str
    expansion: str
    mode: str  # "replace" or "append"


@dataclass(frozen=True)
class Expansion:
    original: str
    expanded: str
    applied: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return bool(self.applied)


@lru_cache
def load_acronyms(path: Path | None = None) -> tuple[Acronym, ...]:
    path = path or get_settings().acronyms_path
    if not path.exists():
        return ()

    data = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        Acronym(term=e["term"], expansion=e["expansion"], mode=e.get("mode", "replace"))
        for e in data.get("acronyms", [])
    )


def expand_acronyms(query: str, acronyms: tuple[Acronym, ...] | None = None) -> Expansion:
    """Expand known acronyms in a query.

    Matching is case-sensitive and word-bounded. Case sensitivity matters
    because several entries are two letters (SV, RV, PR), and lowercase
    matching would rewrite ordinary words. Someone writing 'pr' in lowercase
    is more likely mid-sentence than naming a visa category.
    """
    if acronyms is None:
        acronyms = load_acronyms()

    expanded = query
    applied: list[str] = []

    for acronym in acronyms:
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(acronym.term)}(?![A-Za-z0-9])")
        if not pattern.search(expanded):
            continue

        if acronym.mode == "append":
            replacement = f"{acronym.term} {acronym.expansion}"
        else:
            replacement = acronym.expansion

        expanded = pattern.sub(replacement, expanded)
        applied.append(acronym.term)

    return Expansion(original=query, expanded=expanded, applied=tuple(applied))