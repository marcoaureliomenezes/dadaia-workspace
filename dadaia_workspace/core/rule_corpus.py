"""By-name rule-law corpus reachability — the single scan both doctors share.

Agent instructions cite governance rules by name (the ``workspace-protocol`` rule, the
``bug-hotfix-doctrine`` rule). Each is meant to resolve to a real file at
``.claude/rules/<name>.md``, reachable from every harness. A citation with no file gives
the agent that follows it no law and no error.

This module holds the *semantics* — what counts as a citation, and what unreachable and
uncited mean — because two doctors need the same answer: ``dadaia public doctor``
(projection health, infrastructure) and ``dadaia doctor`` (workspace-state invariants,
features). ``features`` may not import ``infrastructure``, so ``core`` is the only shared
home, and a second implementation would drift out of agreement — which is exactly how the
corpus check ended up verifying nothing on the claude path in the first place.

It performs **no file I/O**: ``core`` is I/O-pure by ratchet (architect A9), and weakening
that invariant to save five lines of globbing in each caller is a bad trade. Callers read
the tree with :data:`CITER_GLOBS` / :data:`RULES_DIR` and hand the text in.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

#: A backticked by-name rule citation — the canonical, unambiguous form.
_CITATION_RE: re.Pattern[str] = re.compile(r"`([a-z][a-z0-9-]+)`\s+rule\b")

#: An un-backticked citation, e.g. the heading "Apply the bug-always-solved rule".
#: Requiring TWO hyphens is what keeps ordinary prose out: "the by-name rule" and "the
#: read-only rule" are adjectives, not slugs. The stated cost is that a one-hyphen slug
#: cited without backticks and missing from the corpus goes unseen; every backticked
#: citation is checked regardless of shape.
_CITATION_PROSE_RE: re.Pattern[str] = re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+){2,})\s+rule\b")

#: Every artifact that cites by-name law. Rules cite each other and the root AGENTS.md
#: cites rules, so scanning only agents/skills reports live law as uncited.
CITER_GLOBS: tuple[str, ...] = (
    ".codex/agents/*.toml",
    ".claude/agents/*.md",
    ".claude/skills/*/SKILL.md",
    ".claude/rules/*.md",
    "AGENTS.md",
)

RULES_DIR = Path(".claude") / "rules"


@dataclass(frozen=True)
class RuleCorpusScan:
    """What the corpus scan found. Empty *cited* means there is nothing to verify."""

    cited: frozenset[str]
    available: frozenset[str]

    @property
    def unreachable(self) -> tuple[str, ...]:
        """Cited by some artifact, but no rule file exists — an error in any harness."""
        return tuple(sorted(self.cited - self.available))

    @property
    def uncited(self) -> tuple[str, ...]:
        """A rule no artifact cites: dead law that still costs context every session."""
        return tuple(sorted(self.available - self.cited))


def citations_in(text: str) -> set[str]:
    """Every by-name rule *text* cites, backticked or in prose."""
    return {match.group(1) for match in _CITATION_RE.finditer(text)} | {
        match.group(1) for match in _CITATION_PROSE_RE.finditer(text)
    }


def scan_rule_corpus(texts: Iterable[str], available: Iterable[str]) -> RuleCorpusScan:
    """Build the scan from artifact *texts* and the rule names present on disk.

    An empty *available* is NOT treated as "nothing to check": if artifacts cite by-name
    law and the corpus is absent entirely, every one of those citations is unreachable,
    and reporting nothing would hide the worst case behind the same clean output as the
    healthy one.
    """
    cited: set[str] = set()
    for text in texts:
        cited |= citations_in(text)
    return RuleCorpusScan(cited=frozenset(cited), available=frozenset(available))
