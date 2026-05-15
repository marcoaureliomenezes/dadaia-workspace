"""Unit tests for PublicAssetService."""

from pathlib import Path

from dadaia_workspace.features.public.service import PublicAssetService
from tests.fakes import FakePublicAssetManager


def test_stage_delegates_to_manager(tmp_path: Path) -> None:
    fake = FakePublicAssetManager()
    svc = PublicAssetService(fake)
    result = svc.stage(tmp_path)
    assert tmp_path in fake.staged
    assert isinstance(result, list)


def test_install_delegates_to_manager(tmp_path: Path) -> None:
    fake = FakePublicAssetManager()
    svc = PublicAssetService(fake)
    result = svc.install(tmp_path, target="claude", force=True)
    assert (tmp_path, "claude", True) in fake.installed
    assert isinstance(result, list)


def test_install_defaults_to_all_no_force(tmp_path: Path) -> None:
    fake = FakePublicAssetManager()
    svc = PublicAssetService(fake)
    svc.install(tmp_path)
    assert (tmp_path, "all", False) in fake.installed


def test_doctor_delegates_to_manager(tmp_path: Path) -> None:
    fake = FakePublicAssetManager()
    svc = PublicAssetService(fake)
    result = svc.doctor(tmp_path)
    assert tmp_path in fake.doctored
    assert isinstance(result, list)
