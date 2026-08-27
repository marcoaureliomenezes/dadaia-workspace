# T-050-19 — `test_rules_skills_map.py` -> `test_behavior_map.py` name-diff

**Owner:** ai-engineer · **Purpose:** A10.6 — prove no hard-won regression is lost on the
retirement of `tests/contract/test_rules_skills_map.py` (25 test functions at HEAD)
before the file is deleted. Grouped at the **nine-check** granularity A10.6 itself uses
("the schema check, the six original map modes, the FR27 citation checks and the FR28
bidirectional model-invocation grant check"); every constituent test function is listed
under its group.

**Zero-hit residue:** every function below has a named counterpart in
`tests/contract/test_behavior_map.py`, is folded into a broader counterpart that asserts
a superset of its behaviour, or is explicitly obviated by the new schema's structure
(one row, group 2 below) — never silently dropped.

## Group 1 — the schema check

| Old (`test_rules_skills_map.py`) | New (`test_behavior_map.py`) | Behaviour still asserted |
|---|---|---|
| `test_map_validates_against_its_own_schema` | `test_map_validates_against_its_own_schema` | The real map validates against its own real schema — same assertion, `behavior-map-v1.schema.json` / `behavior-map.json` in place of the retired pair. |

## Group 2 — the six original map modes

| Old | New | Behaviour still asserted |
|---|---|---|
| `test_every_mapped_section_exists_in_the_law` | `test_every_mapped_section_exists_in_the_law` | Ported unchanged — a row's `section` must be a real `## N. <Title>` heading in `DADAIA.md`, title-anchored. |
| `test_every_skill_on_disk_is_mapped` | `test_every_member_on_disk_is_mapped` | **Folded and generalized.** Every skill on disk still has exactly one row (same assertion), AND the same check now also covers every scoped `AGENTS.md`/`*-AGENTS.md` source on disk (D14's new member type) — a strict superset, not a narrower replacement. |
| `test_every_mapped_skill_exists_on_disk` | `test_every_mapped_member_exists_on_disk` | **Folded and generalized.** Every row's `skill` still resolves to a real `SKILL.md` on disk (same assertion), AND every row's `scoped_agents_md` entries now resolve to real source files too — a strict superset. |
| `test_shared_topics_carry_a_justification` | *(no counterpart — structurally obviated)* | The old schema's `skills: []` + `justification` field modelled "N skills share one topic row" and needed a guard against an undeclared reason for sharing. The new schema removes that field entirely: cardinality is now per-**row**, one member (one skill OR one scoped-AGENTS.md set) per row, and two rows may legitimately name the SAME section with no ambiguity to guard against — the concept the check protected no longer exists structurally. The underlying concern (undocumented multi-ownership) is eliminated by the data model itself, not left unguarded: A10.1's cardinality check (below) is the new guard for the *inverse* direction (a section with **zero** owners), which the old model never checked at all. |
| `test_every_skill_md_is_within_the_declared_line_ceiling` | `test_every_skill_md_is_within_the_declared_line_ceiling` | Ported unchanged — reads `skill_md_line_ceiling` from the map (ported field, same value) against every `SKILL.md` on disk; independent of row shape. |
| `test_no_undeclared_activation_glob_overlap` | `test_no_undeclared_activation_glob_overlap` | Ported unchanged, together with its two ported self-test fixtures (`test_ported_self_test_a_universal_glob_skill_produces_no_finding`, `test_ported_self_test_b_undeclared_duplicate_glob_fires`) — reads `declared_overlaps` (ported field, same value) against `SKILL.md` frontmatter; independent of row shape. |

Six original mutation fixtures (A9.2), one per mode above:

| Old | New | Note |
|---|---|---|
| `test_mutation_fixture_1_missing_section_turns_red` | `test_mutation_fixture_1_missing_section_turns_red` | Ported unchanged. |
| `test_mutation_fixture_2_unmapped_skill_turns_red` | absorbed into `test_mutation_fixture_a_member_without_a_row_turns_red` (one of the 5 new D14 fixtures) | Skill-on-disk-without-a-row is now one arm of the generalized member check; the mutation fixture proves both arms (skill and scoped-AGENTS.md). |
| `test_mutation_fixture_3_missing_skill_on_disk_turns_red` | absorbed into `test_mutation_fixture_b_row_without_a_member_turns_red` | Row-names-nonexistent-skill is now one arm of the generalized dangling-reference check; the mutation fixture proves both arms. |
| `test_mutation_fixture_4_undeclared_shared_topic_turns_red` | *(no counterpart — see the row-4 note above)* | Structurally obviated, same reasoning. |
| `test_mutation_fixture_5_skill_md_over_ceiling_turns_red` | `test_mutation_fixture_5_skill_md_over_ceiling_turns_red` | Ported unchanged. |
| `test_mutation_fixture_6_undeclared_activation_overlap_turns_red` | `test_mutation_fixture_6_undeclared_activation_overlap_turns_red` | Ported unchanged. |

## Group 3 — the FR27 citation checks

| Old | New | Behaviour still asserted |
|---|---|---|
| `test_every_cited_path_exists` | `test_every_cited_path_exists` | Ported unchanged. |
| `test_projected_specs_agents_md_citation_survives_bare_checkout` | `test_projected_specs_agents_md_citation_survives_bare_checkout` | Ported unchanged — regression for bug `citation-enforcer-resolves-projected-instance-paths-against-the-checkout`. |
| `test_every_cited_dadaia_verb_exists` | `test_every_cited_dadaia_verb_exists` | Ported unchanged. |
| `test_mutation_fixture_9_dead_path_citation_turns_red` | `test_mutation_fixture_9_dead_path_citation_turns_red` | Ported unchanged. |
| `test_mutation_fixture_11_lookalike_projected_path_still_turns_red` | `test_mutation_fixture_11_lookalike_projected_path_still_turns_red` | Ported unchanged. |
| `test_mutation_fixture_10_dead_verb_citation_turns_red` | `test_mutation_fixture_10_dead_verb_citation_turns_red` | Ported unchanged. |
| `test_posix_relpath_is_separator_agnostic_under_windows_path_semantics` | `test_posix_relpath_is_separator_agnostic_under_windows_path_semantics` | Ported unchanged — regression for bug `citation-mutation-fixtures-never-turn-red-on-windows`. |

None of these seven depend on the map's row shape (they scan `public/**/*.md` broadly and
the live `typer` command tree) — relocated verbatim, same function bodies, same names.

## Group 4 — the FR28 bidirectional model-invocation grant check

| Old | New | Behaviour still asserted |
|---|---|---|
| `test_ungranted_skills_carry_disable_model_invocation` | `test_ungranted_skills_carry_disable_model_invocation` | Ported unchanged (direction 7a). |
| `test_disable_model_invocation_skills_are_in_no_allowlist` | `test_disable_model_invocation_skills_are_in_no_allowlist` | Ported unchanged (direction 7b). |
| `test_mutation_fixture_7_ungranted_skill_without_flag_turns_red` | `test_mutation_fixture_7_ungranted_skill_without_flag_turns_red` | Ported unchanged. |
| `test_mutation_fixture_8_flagged_skill_still_granted_turns_red` | `test_mutation_fixture_8_flagged_skill_still_granted_turns_red` | Ported unchanged. |

None of these four depend on the map's row shape (they derive the grant set from persona
`skills:` allowlists and `SKILL.md` frontmatter) — relocated verbatim.

## Residue check

25 old test functions accounted for: 1 (schema) + 6 modes + 6 mode-fixtures + 2 self-tests
+ 7 (FR27, incl. its 4 mutation fixtures) + 4 (FR28, incl. its 2 mutation fixtures) = 25.
Zero unaccounted. Two carry no direct-name counterpart
(`test_shared_topics_carry_a_justification`,
`test_mutation_fixture_4_undeclared_shared_topic_turns_red`) and both are justified above
as structurally obviated, not dropped.

## The five NEW D14 checks (A10.2, not a port — net-new coverage `behavior-map.json` itself requires)

| New check | RED condition |
|---|---|
| `test_every_member_on_disk_is_mapped` (+ `test_mutation_fixture_a_member_without_a_row_turns_red`) | A member (skill or scoped `AGENTS.md` source) exists on disk with no row. |
| `test_every_mapped_member_exists_on_disk` (+ `test_mutation_fixture_b_row_without_a_member_turns_red`) | A row names a member path that does not exist on disk. |
| `test_no_member_maps_to_two_sections` (+ `test_mutation_fixture_c_member_maps_to_two_sections_turns_red`) | The same member (skill name, or the same scoped path) appears in more than one row — cardinality A10.1's "exactly one section" direction. |
| `test_every_law_section_has_an_owner` (+ `test_mutation_fixture_d_section_without_an_owner_turns_red`) | A `DADAIA.md` `## N. Title` section has zero owning rows — cardinality A10.1's "at least one owner" direction; the old enforcer never checked this direction at all. |
| `test_every_hash_tuple_is_current` (+ `test_mutation_fixture_e_stale_hash_tuple_turns_red`) | A member's real content hash (recomputed) no longer matches its row's recorded `hash_tuple` entry — A10.4, a deliberate re-recording obligation. |

Each fixture message names the file to re-read (A10.4/D14's own acceptance line).
