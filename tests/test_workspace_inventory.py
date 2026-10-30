import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


spec = importlib.util.spec_from_file_location(
    "workspace_inventory", Path(__file__).resolve().parents[1] / "scripts/workspace_inventory.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    def git_files(*args, **kwargs):
        names = [path.name for path in tmp_path.iterdir() if path.is_file()]
        return SimpleNamespace(stdout=b"\0".join(name.encode("utf-8") for name in sorted(names)) + b"\0")
    monkeypatch.setattr(module.subprocess, "run", git_files)
    return tmp_path


def test_inventory_keeps_unicode_paths_and_counts_ignored_outputs(workspace):
    (workspace / "待保存 正文.md").write_bytes(b"draft")
    run = workspace / ".local/runs/task"
    run.mkdir(parents=True)
    (run / "result.json").write_bytes(b"{}")
    before = {path.relative_to(workspace): path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    result = module.inventory(workspace)
    assert result["untracked"] == ["待保存 正文.md"]
    assert result["groups"][0]["bytes"] == 5
    assert result["local_runs"]["files"] == 1
    assert result["local_runs"]["bytes"] == 2
    assert {path.relative_to(workspace): path.read_bytes() for path in workspace.rglob("*") if path.is_file()} == before


def test_missing_local_directory_is_empty(workspace):
    result = module.inventory(workspace)
    assert result["untracked_entries"] == 0
    assert result["local_runs"] == {"files": 0, "bytes": 0, "links": [], "errors": []}


def test_scan_does_not_follow_directory_link(tmp_path):
    source = tmp_path / "outside"
    source.mkdir()
    (source / "keep.txt").write_bytes(b"preserve")
    root = tmp_path / "runs"
    root.mkdir()
    try:
        (root / "linked").symlink_to(source, target_is_directory=True)
    except OSError:
        pytest.skip("当前系统不允许创建测试目录链接")
    result = module.scan_tree(root)
    assert result["files"] == 0
    assert result["links"] == ["linked"]
    assert (source / "keep.txt").read_bytes() == b"preserve"
