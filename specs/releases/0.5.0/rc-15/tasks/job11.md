# Job 11 — the ADR list is rendered from the ledger, and a `measured_by` must resolve (FR10, code half)

**Status:** Draft

Wave 4. Two ledger-reading rules in `doctor_adr.py`, the ADR code's one module: a renderer of one `ARCHITECTURE.md` block and a resolver of `measured_by`, plus the lint exemption. ADR 0251 (accepted 2026-10-13) (c) and (d). No memory file is written by this job, and no canon-fingerprinted file changes (`FIXED_SECTIONS` stays as it is; Job 12 owns the pin).

- **Seams closed.**
  - The block uses the existing marker grammar of `core/fixed_sections.py` (`render_fixed_section`, `extract_fixed_section`) with id `adr-list` in `memory/ARCHITECTURE.md`. It is judged only where the markers exist: no markers, no finding. Until the Reconciliation inserts them every job gate stays green, and the repo's own doctor cannot go red between this merge and the Reconciliation.
  - Content: one line `- <id> — <title>` per record with status `accepted`, in id order (a superseded record has status `superseded`).
  - A `measured_by` resolves when it holds a token that is a tracked path (`git ls-files` of the specs repo), a `path::name` node id whose file is tracked and names the node, a rule code of the doctor's registry or lint contract, or a key under `jobs:` of any tracked `*.yml`. Resolution reads local files and local git only; a repo with no CI config simply resolves no CI job.
  - The resolver is a public function `unresolved_measured_by(specs_dir)` returning `(id, text)` pairs, used by the renderer's refusal and by the triage step of the PLAN.
  - Refusal: the renderer raises when the list is non-empty; the check reports it as FIXED-2 with the ids and one fix line, and `--fix` writes nothing. A block that differs from a clean render is FIXED-2 with `--fix` regenerating it. If the rule registry admits one rule per code, the block check joins `check_fixed_sections`' rule.
  - MEM-NARRATIVE-1 skips lines between any fixed-section markers, as it skips fenced code; line numbers of later errors do not move. `test_memory_lint.py:346-350` and `:427-431` stay unedited (no order covers them).
  - Growth reason (G3, ADR 0251): about +60 to +90 production lines (inspection estimate), against the law and label lines Job 12 and the Reconciliation delete.
- Test-side first: T1, T2, T3 (disjoint `W:`). Then T4, then T5, T6 (disjoint).
- Pre-review checklist: one resolver, one renderer, no second ADR reader (`_ids`/`adr_record_issues` reused); no cross-component import; sweep `git grep -n 'decisions.jsonl' -- dadaia_workspace/features` (readers before and after); no platform fact; net lines stated above.

Tasks: 6 (0 jr, 6 sr). `who` names the dispatched role (`dd-release-definition` §5).

| task | who | AC | `W:` | outcome |
|---|---|---|---|---|
| J11.T1 | sr | AC10.3 | `tests/features/specs/test_doctor_adr.py` | RED, unit: an accepted record naming a missing path is unresolved, one naming a tracked `path::name` node id resolves; superseded, proposed and rejected records are not judged; the refusal carries one fix line. Owner this file |
| J11.T2 | sr | AC10.4 | `tests/features/specs/test_doctor__doctor_fixed_sections.py` | RED, integration: a file with the markers and a stale block is FIXED-2 and `--fix` regenerates it; a file without markers yields nothing; an unresolved `measured_by` refuses the regeneration and writes nothing. Owner this file |
| J11.T3 | sr | AC10.4 | `tests/features/specs/test_memory_lint.py` | RED, unit (new case only): a candidate-id line inside the block markers is no MEM-NARRATIVE-1 error, the same line outside is. Owner this file |
| J11.T4 | sr | AC10.3, AC10.4 | `dadaia_workspace/features/specs/doctor_adr.py` | the resolver and the renderer of the intro. Owner T1. After T1 |
| J11.T5 | sr | AC10.4 | `dadaia_workspace/features/specs/doctor_memory.py`, `dadaia_workspace/features/specs/rules.py` | the check and its `--fix` over the block. Owner T2. After T2, T4 |
| J11.T6 | sr | AC10.4 | `dadaia_workspace/features/specs/memory_lint.py` | the marker skip. Owner T3. After T3 |
