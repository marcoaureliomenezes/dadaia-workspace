"""Declarative role→memory-atom map + the ONE resolve-and-inject helper (v0.1.57 FR2 / A1).

Before this release role grounding depended on per-fragment luck: an atom reached a worker
only if some fragment author remembered to declare it in ``dynamic_inputs`` *and* a selector
was wired for that input. This module makes grounding a **guarantee**: a step's ``role`` alone
selects the memory atom(s), resolved at Layer-2 prompt assembly independently of any fragment
declaration or wired :class:`ContextSelector`.

Two things live here, and **only** here (never copy-pasted into a workflow body):

* :data:`ROLE_ATOM_MAP` — the declarative default map. Each value is the atom's path relative
  to the active context's ``specs_dir``.
* :func:`inject_role_atoms` — the single resolve-and-inject helper consumed by all THREE
  Layer-2 assembly surfaces (the ``FragmentGateWorkflow`` base, :class:`LifecyclePipeline`, and
  :class:`LifecyclePhaseWorkflow`). It resolves the role → reads the atom file under the given
  ``specs_dir`` → appends a labelled context block to the prompt → records each atom ref in the
  run's :class:`InjectedContext` refs (the Layer-2 verifiability seam — FR4).

Fail-open by construction: a multi-role label is comma-split and each named role resolved in
order; an unmapped role, a missing atom file, or an un-wired surface (``specs_dir is None``)
injects nothing and leaves the run + prompt byte-identical.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import InjectedContext, LifecycleRun

#: The declarative role → memory-atom map (FR2). Each value is the atom's path relative to the
#: active context's ``specs_dir``. Injection is INDEPENDENT of a fragment's ``dynamic_inputs``:
#: the step's ``role`` alone selects the atom(s), so grounding is guaranteed by the map, not by
#: per-fragment declaration luck (the frontmatter-inert defect this release removes). A role not
#: listed here (e.g. ``python``, ``security-reviewer``, ``project-auditor``) injects nothing.
ROLE_ATOM_MAP: dict[str, str] = {
    "software-architect": "memory/architecture.md",
    "qa-engineer": "memory/quality-assurance.md",
    "product-engineer": "memory/product/catalog.json",
}


def _atom_ref(relpath: str) -> str:
    """Stable, host-independent ref for a recorded atom (``specs/``-prefixed, POSIX).

    Mirrors :meth:`ContextSelector._specs_ref` (which renders refs relative to
    ``specs_dir.parent``), so a role-mapped atom ref reads the same as a selector-resolved ref
    in the run's ``InjectedContext``.
    """
    return f"specs/{relpath}"


def _split_roles(role: str) -> tuple[str, ...]:
    """Comma-split a (possibly multi-)role label (e.g. ``"qa-engineer, software-architect"``)."""
    return tuple(part.strip() for part in role.split(",") if part.strip())


def _atom_block(role: str, ref: str, content: str) -> str:
    """One labelled role-atom context block appended to a worker prompt."""
    return f"<!-- role-atom:{role}:{ref} -->\n{content}".rstrip()


def resolve_role_atoms(role: str, specs_dir: Path | None) -> tuple[tuple[str, str, str], ...]:
    """Resolve *role*'s mapped memory atom(s) to ``(role_name, ref, content)`` triples.

    Multi-role labels are comma-split and each named role resolved in declaration order. A role
    with no mapping yields nothing; a mapped atom whose file is absent under *specs_dir* is
    skipped (fail-open — the caller never crashes on a missing atom); ``specs_dir is None``
    (a surface that is not production-wired) yields nothing.
    """
    if specs_dir is None:
        return ()
    out: list[tuple[str, str, str]] = []
    for named in _split_roles(role):
        relpath = ROLE_ATOM_MAP.get(named)
        if relpath is None:
            continue
        try:
            content = (specs_dir / relpath).read_text(encoding="utf-8")
        except OSError:
            # Missing / unreadable atom file — fail-open, no injection, no crash.
            continue
        out.append((named, _atom_ref(relpath), content))
    return tuple(out)


def _record_atom_refs(run: LifecycleRun, step_label: str, refs: tuple[str, ...]) -> LifecycleRun:
    """Merge *refs* into the run's :class:`InjectedContext` entry for *step_label*.

    When an entry for *step_label* already exists (e.g. the base recorded the selector audit
    via :func:`record_injected_context`), the new atom refs are appended to it (de-duplicated),
    preserving every other field via :func:`dataclasses.replace` so a later
    ``record_prompt_composition`` still enriches the same entry. When no entry exists yet (the
    selector-less pipeline / phase_workflow path) a fresh entry carrying only the atom refs is
    appended, so the run persists the Layer-2 grounding proof either way.
    """
    entries = list(run.injected_context)
    target = next((i for i in reversed(range(len(entries))) if entries[i].step == step_label), None)
    if target is None:
        entries.append(InjectedContext(step=step_label, refs=refs))
    else:
        existing = entries[target]
        merged = existing.refs + tuple(r for r in refs if r not in existing.refs)
        entries[target] = replace(existing, refs=merged)
    return replace(run, injected_context=tuple(entries))


def inject_role_atoms(
    *,
    run: LifecycleRun,
    step_label: str,
    role: str,
    specs_dir: Path | None,
    prompt: str,
) -> tuple[LifecycleRun, str]:
    """Append *role*'s mapped memory atom(s) to *prompt* + record their refs on *run* (A1).

    The ONE resolve-and-inject helper consumed by all three Layer-2 assembly surfaces
    (``FragmentGateWorkflow`` base, :class:`LifecyclePipeline`, :class:`LifecyclePhaseWorkflow`)
    — never copy-pasted. It:

    1. resolves *role* to its mapped atom(s) and reads each under *specs_dir*;
    2. appends one labelled context block per atom to *prompt* (the grounding that appears in
       the assembled worker prompt); and
    3. records each atom ref in the run's ``InjectedContext.refs`` for *step_label* (the
       mechanical Layer-2 verifiability seam the FR3 coherence doctor checks).

    Multi-role comma-split; an unmapped role, a missing atom file, or ``specs_dir is None``
    injects nothing and returns the run + prompt unchanged (fail-open).
    """
    atoms = resolve_role_atoms(role, specs_dir)
    if not atoms:
        return run, prompt
    blocks = [_atom_block(role_name, ref, content) for role_name, ref, content in atoms]
    new_prompt = "\n\n".join([part for part in (prompt, *blocks) if part])
    refs = tuple(ref for _, ref, _ in atoms)
    return _record_atom_refs(run, step_label, refs), new_prompt


__all__ = [
    "ROLE_ATOM_MAP",
    "inject_role_atoms",
    "resolve_role_atoms",
]
