"""Unit tests for PublicAssetService.

Thin service; real behavior owned by integration public-assets suites. These are pure
delegate-echo tests, collapsed to one fn covering stage/install/doctor delegation +
install's default args.
"""

from pathlib import Path

from dadaia_workspace.features.public.service import PublicAssetService
from tests.fakes import FakePublicAssetManager


def test_stage_install_doctor_delegate_to_manager(tmp_path: Path) -> None:
    fake = FakePublicAssetManager()
    svc = PublicAssetService(fake)

    stage_result = svc.stage(tmp_path)
    assert tmp_path in fake.staged
    assert isinstance(stage_result, list)

    install_result = svc.install(tmp_path, target="claude", force=True)
    assert (tmp_path, "claude", True) in fake.installed
    assert isinstance(install_result, list)

    svc.install(tmp_path)
    assert (tmp_path, "all", False) in fake.installed

    doctor_result = svc.doctor(tmp_path)
    assert tmp_path in fake.doctored
    # The service returns the typed DoctorReport aggregate (the verdict authority).
    assert doctor_result.blocking is False
    assert "[ok] fake" in doctor_result.rendered()
