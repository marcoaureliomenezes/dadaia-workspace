# D-OC-1 Design Note

**Author:** ai-engineer (T-OCV-05a)
**Consumed by:** software-engineer-python implementing invariant D-OC-1 in `dadaia_workspace/features/doctor/` (T-OCV-06b)
**Status:** Implemented — all tasks green as of orchestration-consolidation-v1 closure.

---

**Target reader:** `software-engineer-python` implementing invariant D-OC-1 in
`dadaia specs doctor` (T-OCV-06b).

**Source files:**
- PM router: `dadaia_workspace/public/agents/project-manager.md`
- Skill: `dadaia_workspace/public/skills/project-orchestration/SKILL.md`
- Workflow files: `dadaia_workspace/public/workflows/*.workflow.md`

---

## 1. Parsing Logic

**Extracting Tier-1 names from `project-manager.md` Step-3:**

The Tier-1 table appears under the heading:
```
#### Tier-1 — Engine-backed workflows (call `dadaia orchestrate run <name> --input ...`)
```

Parse it as a Markdown table. The workflow name is in the second column (`| Workflow name |`).
Use this regex on each table data row:
```python
import re

TIER1_TABLE_ROW = re.compile(
    r'^\|\s*`([^`]+)`\s*\|\s*`public/workflows/([^`]+)\.workflow\.md`',
    re.MULTILINE
)
```
This captures `(demand_label, workflow_name)` pairs. The workflow name (group 2) is
what maps to a `*.workflow.md` file.

Alternatively, a simpler single-column scan for the workflow name column:
```python
TIER1_NAME = re.compile(
    r'^\|\s+`([a-z][a-z0-9-]+)`\s+\|\s+`public/workflows/\1\.workflow\.md`',
    re.MULTILINE
)
```
Capture group 1 is the canonical Tier-1 workflow name.

**Extracting Tier-2 names from `project-manager.md` Step-3:**

The Tier-2 table appears under the heading:
```
#### Tier-2 — PM Playbooks (compose inline from `project-orchestration` skill)
```

Parse the second column (`| Playbook name |`) of this table:
```python
TIER2_NAME = re.compile(
    r'^\|\s+`([a-z][a-z0-9-]+)`\s*\|',
    re.MULTILINE
)
```
Apply only to lines between the Tier-2 heading and the next `###` or `---` boundary.
Capture group 1 is the canonical Tier-2 playbook name.

**Note:** The `spec-refinement` entry in Tier-2 includes a parenthetical note. Strip
everything after the first backtick-enclosed name. Example:
```
| `spec-refinement` (Tier-2 path; ...) | ...
```
Extract only `spec-refinement`.

**Extracting `### Playbook — <name>` headings from SKILL.md:**

```python
PLAYBOOK_HEADING = re.compile(
    r'^###\s+Playbook\s+—\s+([a-z][a-z0-9-]+)(\s+\[deprecated\])?',
    re.MULTILINE | re.IGNORECASE
)
```
Capture group 1 is the playbook name. Capture group 2 (if present and equals
`[deprecated]`) marks the playbook as deprecated — it is exempt from the reverse check.

**Note on the `spec-refinement` section heading:** The current SKILL.md uses:
```
### spec-refinement — Tier-1 engine-backed workflow
```
This does NOT match `### Playbook — spec-refinement` and MUST NOT be treated as a
Tier-2 playbook heading. The D-OC-1 reverse check only matches headings of the exact
form `### Playbook — <name>`. The `spec-refinement` Tier-1 section heading is
intentionally different.

---

## 2. The Precise D-OC-1 Rule Statement

**Invariant D-OC-1 (bidirectional orchestration registry coherence):**

> Every name referenced in the two-tier router in `project-manager.md` Step-3 AND in
> `project-orchestration/SKILL.md` must resolve unambiguously:
>
> **Forward (router → artifact):**
> - Every Tier-1 name in the PM router MUST have a corresponding file at
>   `dadaia_workspace/public/workflows/<name>.workflow.md`.
> - Every Tier-2 name in the PM router MUST have a corresponding
>   `### Playbook — <name>` heading in SKILL.md.
>
> **Reverse (artifact → router):**
> - Every `### Playbook — <name>` heading in SKILL.md MUST appear as a Tier-2 row in
>   the PM router table, OR carry the annotation `[deprecated]` in the heading itself
>   (`### Playbook — <name> [deprecated]`).
>
> A dangling reference in either direction is a **hard error** (non-zero exit, `[error]`
> line in `dadaia specs doctor` output).

---

## 3. Parsing Boundary Details

To scope the Tier-2 regex to only the Tier-2 table (avoiding false matches in prose),
use a two-pass approach:

1. Split `project-manager.md` on `#### Tier-1` and `#### Tier-2` headings to isolate
   each tier's block.
2. Apply the respective regex only within that block.
3. Stop at the next `####` or `###` heading.

Python sketch:
```python
from pathlib import Path
import re

def _split_tier_blocks(text: str) -> tuple[str, str]:
    tier1_match = re.search(r'#### Tier-1[^\n]*\n', text)
    tier2_match = re.search(r'#### Tier-2[^\n]*\n', text)
    if not tier1_match or not tier2_match:
        return "", ""
    tier1_block = text[tier1_match.end():tier2_match.start()]
    # Tier-2 block ends at next `###` or end of file
    tier2_end = re.search(r'^###', text[tier2_match.end():], re.MULTILINE)
    tier2_block = (
        text[tier2_match.end(): tier2_match.end() + tier2_end.start()]
        if tier2_end else text[tier2_match.end():]
    )
    return tier1_block, tier2_block


def extract_tier1_names(pm_text: str) -> list[str]:
    tier1_block, _ = _split_tier_blocks(pm_text)
    return re.findall(
        r'^\|\s+`([a-z][a-z0-9-]+)`\s+\|\s+`public/workflows/',
        tier1_block, re.MULTILINE
    )


def extract_tier2_names(pm_text: str) -> list[str]:
    _, tier2_block = _split_tier_blocks(pm_text)
    return re.findall(r'^\|\s+`([a-z][a-z0-9-]+)`', tier2_block, re.MULTILINE)


def extract_playbook_headings(skill_text: str) -> dict[str, bool]:
    """Returns {name: is_deprecated}."""
    matches = re.findall(
        r'^###\s+Playbook\s+—\s+([a-z][a-z0-9-]+)(\s+\[deprecated\])?',
        skill_text, re.MULTILINE | re.IGNORECASE
    )
    return {name: bool(dep.strip()) for name, dep in matches}
```

---

## 4. Expected Error Message Format

All D-OC-1 error lines must follow this format so they are parseable by the doctor
output scanner and the unit test assertions:

```
[error] D-OC-1: Tier-1 name '<name>' has no workflow file at public/workflows/<name>.workflow.md
[error] D-OC-1: Tier-2 name '<name>' has no playbook heading '### Playbook — <name>' in SKILL.md
[error] D-OC-1: Playbook heading '### Playbook — <name>' in SKILL.md has no Tier-2 router row in project-manager.md (add it or annotate [deprecated])
```

On success (no dangling references), emit:
```
[ok] D-OC-1: orchestration registry coherence — N Tier-1 workflows, M Tier-2 playbooks, K playbook headings — all references resolved
```

The doctor command must exit non-zero if any `[error] D-OC-1:` line is emitted.

---

## 5. Implementation Location Hint

The doctor invariants live in `dadaia_workspace/features/doctor/` (inspect for the
existing invariant registration pattern — likely a list of check functions, each
returning a list of `DoctorFinding` objects or equivalent). The D-OC-1 check should
be registered at the same level as existing checks, with label `"D-OC-1"`.

The check receives the absolute path to the `dadaia_workspace/public/` directory and
reads the three relevant files from there. No network access; stdlib `re` + `pathlib`
only.
