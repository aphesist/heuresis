import json
from pathlib import Path

import pytest

from heuresis.v2.locked import manifest as M


@pytest.fixture
def tree(tmp_path):
    def w(rel, text="x"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    w("src/heuresis/locked/verify.py", "v")
    w("src/heuresis/locked/__pycache__/verify.pyc", "c")
    w("src/heuresis/v2/locked/gates.py", "g")
    w("src/heuresis/v2/locked/policy.json", "{}")
    w("src/heuresis/store.py", "s")
    w("src/heuresis/tools/calc.py", "c")
    w("src/heuresis/bench/stats.py", "b")
    w("src/heuresis/bench/other.py", "not protected")
    w("src/heuresis/evolve/loop.py", "e")
    w("src/heuresis/v2/bind.py", "bind")
    w("src/heuresis/v2/surface/default.json", "{}")
    w("src/heuresis/engine.py", "not protected")
    return tmp_path


def test_protected_files_selection(tree):
    files = M.protected_files(tree)
    assert set(files) == {
        "src/heuresis/locked/verify.py", "src/heuresis/v2/locked/gates.py",
        "src/heuresis/v2/locked/policy.json", "src/heuresis/store.py",
        "src/heuresis/tools/calc.py", "src/heuresis/bench/stats.py",
        "src/heuresis/evolve/loop.py", "src/heuresis/v2/bind.py"}
    assert list(files) == sorted(files)
    assert len(next(iter(files.values()))) == 64


def test_write_and_verify(tree):
    path = M.write_manifest(tree)
    assert path == tree / "src/heuresis/v2/locked/PROTECTED.json"
    data = json.loads(path.read_text())
    assert data["files"] == M.protected_files(tree) and data["hash"] == M.protected_hash(tree)
    assert M.verify_manifest(tree) == []
    # the manifest itself is not protected: writing it again changes nothing
    M.write_manifest(tree)
    assert M.protected_hash(tree) == data["hash"]


def test_verify_detects_changed_missing_new(tree):
    M.write_manifest(tree)
    (tree / "src/heuresis/store.py").write_text("changed")
    (tree / "src/heuresis/tools/calc.py").unlink()
    (tree / "src/heuresis/evolve/new.py").write_text("n")
    (tree / "src/heuresis/engine.py").write_text("free to change")
    out = M.verify_manifest(tree)
    assert out == ["changed: src/heuresis/store.py", "missing: src/heuresis/tools/calc.py",
                   "new: src/heuresis/evolve/new.py"]
    assert M.protected_hash(tree) != json.loads(
        (tree / "src/heuresis/v2/locked/PROTECTED.json").read_text())["hash"]


def test_verify_without_manifest(tree):
    assert "PROTECTED.json" in M.verify_manifest(tree)[0]
    (tree / "src/heuresis/v2/locked/PROTECTED.json").write_text("{bad")
    assert "PROTECTED.json" in M.verify_manifest(tree)[0]


def test_default_root_is_the_repository():
    root = M.default_root()
    assert (root / "src" / "heuresis" / "v2" / "locked" / "manifest.py").is_file()
    assert (root / "pyproject.toml").is_file()
    files = M.protected_files()
    assert "src/heuresis/locked/decide.py" in files and "src/heuresis/store.py" in files
    assert all("__pycache__" not in f for f in files)


@pytest.mark.parametrize("path,ok", [
    ("src/heuresis/v2/surface/default.json", True),
    ("src/heuresis/v2/surface/prompts/agent_more.txt", True),
    ("src/heuresis/v2/surface/prompts/agent_more.legal_br.txt", True),
    ("src/heuresis/v2/surface/./domain.x.json", True),
    ("src/heuresis/v2/surface/engine.py", False),
    ("src/heuresis/v2/surface/prompts/x.md", False),
    ("src/heuresis/v2/surface/noext", False),
    ("src/heuresis/v2/locked/policy.json", False),
    ("src/heuresis/v2/surface_evil/x.json", False),
    ("src/heuresis/v2/surface", False),
    ("src/heuresis/v2/surface/../locked/policy.json", False),
    ("../x.json", False),
    ("/etc/passwd.json", False),
    ("/src/heuresis/v2/surface/default.json", False),
    ("C:/x/default.json", False),
    ("src\\heuresis\\v2\\surface\\default.json", True),
    ("src\\heuresis\\v2\\surface\\..\\locked\\p.json", False),
    ("~/x.json", False),
    ("pyproject.toml", False),
    ("", False),
])
def test_candidate_paths(path, ok):
    assert (M.check_candidate_paths([path]) == []) is ok


def test_candidate_paths_reports_each():
    out = M.check_candidate_paths(["src/heuresis/v2/surface/a.json", "x.py", "../y.txt"])
    assert len(out) == 2 and out[0].startswith("x.py") and out[1].startswith("../y.txt")
    assert M.check_candidate_paths([]) == []


def test_the_protected_manifest_matches_the_tree():
    """A change to a protected file must come with a deliberate `heuresis lock`."""
    from heuresis.v2.locked import manifest
    assert manifest.verify_manifest() == []
