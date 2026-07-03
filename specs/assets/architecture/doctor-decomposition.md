# `features/specs/doctor` — SpecsDoctor coordinator + validator siblings

**Release origin:** v0.1.55 (Architecture Decomposition, FR1). This class diagram is the
canonical picture of the decomposed `features/specs/doctor` subsystem: a thin `SpecsDoctor`
**coordinator** that owns `check()`/`fix()` ORDER and delegates all LOGIC to six
single-responsibility validator siblings, plus two shared leaf modules
(`doctor_types`, `doctor_common`). It replaces the former 2,830-line god module.

The two feature-boundary imports are **confined** to exactly one validator each:
`doctor_coherence` is the sole holder of the `spec_context.{lease, session_identity}` edge, and
`doctor_memory` is the sole holder of the lazy `infrastructure.subprocess_runner` edge. The
coordinator holds neither — its `pid_probe` seam is typed against the `doctor_types.PidProbe`
leaf alias, so it carries no `spec_context` cross-feature edge (R-1 cap invariant, cross-feature
stays 13).

```mermaid
classDiagram
    class SpecsDoctor {
        +check() list~SpecsDoctorIssue~
        +fix() list~SpecsDoctorIssue~
        -pid_probe doctor_types.PidProbe
    }
    class StructuralValidator {
        +check_tree1_foundation()
        +check_tree4_required_dirs()
        +fix_tree4()
    }
    class MemoryValidator {
        +check_memory_files()
        +check_cat1_catalog_sync()
        +check_lint1_memory_atoms()
    }
    class ReleaseValidator {
        +check_active_md()
        +check_release_semver_naming()
        +check_phase_markers_coherence()
    }
    class ClosureAuditValidator {
        +check_archive_closures()
        +check_audit_disposition()
        +fix_archive_dir()
    }
    class GovernanceValidator {
        +check_backlog_schema()
        +check_bug_status_canon()
        +check_bugs_jsonl_invariant()
    }
    class CoherenceValidator {
        +check_constitution()
        +check_orchestration_registry()
        +check_lease_session_coherence()
    }
    class doctor_types {
        <<leaf module>>
        Severity
        SpecsDoctorIssue
        PidProbe
    }
    class doctor_common {
        <<leaf module>>
        read_active_md()
        iter_all_release_dirs()
    }

    SpecsDoctor --> StructuralValidator : owns ORDER
    SpecsDoctor --> MemoryValidator : owns ORDER
    SpecsDoctor --> ReleaseValidator : owns ORDER
    SpecsDoctor --> ClosureAuditValidator : owns ORDER
    SpecsDoctor --> GovernanceValidator : owns ORDER
    SpecsDoctor --> CoherenceValidator : owns ORDER
    StructuralValidator ..> doctor_types : uses
    MemoryValidator ..> doctor_types : uses
    ReleaseValidator ..> doctor_common : uses
    ClosureAuditValidator ..> doctor_common : uses
    GovernanceValidator ..> doctor_common : uses
    CoherenceValidator ..> doctor_types : uses

    note for CoherenceValidator "SOLE holder of the spec_context.lease + session_identity import (boundary edge)"
    note for MemoryValidator "SOLE holder of the lazy infrastructure.subprocess_runner import (boundary edge)"
    note for SpecsDoctor "imports NEITHER spec_context NOR subprocess_runner — pid_probe typed against the doctor_types.PidProbe leaf"
```

**Regeneration law.** Regenerate at the closure of every structural release (any rename,
split, or merge of the `SpecsDoctor` coordinator or its validator siblings). The class names
above are pinned by the introspection drift-guard
`tests/contract/test_architecture_diagrams_current.py`, which imports the live `doctor_*`
modules and fails if a diagrammed class name goes stale or a live validator is missing.
