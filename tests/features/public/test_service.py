"""Unit tests for PublicAssetService.

Thin service; real behavior owned by integration public-assets suites. These are pure
delegate-echo tests, collapsed to one fn covering stage/install/doctor delegation +
install's default args.
"""

from pathlib import Path

from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.features.public.service import PublicAssetService
from tests.fakes import FakePublicAssetManager
from tests.helpers.oslib import write_text


def test_stage_install_doctor_delegate_to_manager(tmp_path: Path) -> None:
    fake = FakePublicAssetManager()
    svc = PublicAssetService(fake)

    stage_result = svc.stage(tmp_path)
    assert tmp_path in fake.staged
    assert isinstance(stage_result, list)

    install_result = svc.install(tmp_path, harness="claude", force=True)
    assert (tmp_path, "claude", True) in fake.installed
    assert isinstance(install_result, list)

    svc.install(tmp_path)
    assert (tmp_path, None, False) in fake.installed

    doctor_result = svc.doctor(tmp_path)
    assert tmp_path in fake.doctored
    # The service returns the typed DoctorReport aggregate (the verdict authority).
    assert doctor_result.blocking is False
    assert "[ok] fake" in doctor_result.rendered()


class _Blocking(FakePublicAssetManager):
    def doctor(self, workspace_root: Path) -> list[DoctorLine]:
        return [DoctorLine(DoctorStatus.ERROR, "x")]


def test_a_blocking_line_without_a_fix_is_remedied_by_the_owners_projected_act(
    tmp_path: Path,
) -> None:
    svc = PublicAssetService(_Blocking())
    _, remedy = svc.verdict(tmp_path)
    assert remedy == (
        "Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument"
    )

    write_text(tmp_path / ".dadaia" / "states" / "spec_contexts.json", "{}")
    assert svc.verdict(tmp_path)[1] == fix_line(tmp_path.resolve(), "public", "install")
