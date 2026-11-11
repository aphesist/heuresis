import shutil
from pathlib import Path

import heuresis.locked as locked_pkg
from heuresis.locked.guard import check_diff, locked_hash


def test_hash_stable_and_matches_copy(tmp_path):
    h = locked_hash()
    assert h == locked_hash() and len(h) == 64
    src = Path(locked_pkg.__file__).parent
    for f in src.glob("*.py"):
        shutil.copy(f, tmp_path / f.name)
    assert locked_hash(tmp_path) == h


def test_hash_detects_change_add_and_rename(tmp_path):
    src = Path(locked_pkg.__file__).parent
    for f in src.glob("*.py"):
        shutil.copy(f, tmp_path / f.name)
    h = locked_hash(tmp_path)
    (tmp_path / "scoring.py").write_text((tmp_path / "scoring.py").read_text() + "\n# x\n")
    h2 = locked_hash(tmp_path)
    assert h2 != h
    (tmp_path / "extra.py").write_text("")
    assert locked_hash(tmp_path) != h2
    (tmp_path / "extra.py").rename(tmp_path / "extra2.py")
    assert locked_hash(tmp_path) not in (h, h2)


def test_check_diff():
    ok = ["src/heuresis/surface/default.json", "./src/heuresis/surface/prompts.py",
          "src\\heuresis\\surface\\config.py"]
    assert check_diff(ok) == []
    bad = ["src/heuresis/locked/verify.py", "tests/test_x.py", "src/heuresis/surface",
           "src/heuresis/surface/../locked/x.py", "./src/heuresis/surface/../../model.py",
           "src/heuresis/surfaceX/a.py", "/src/heuresis/surface/a.py"]
    assert check_diff(ok + bad) == bad
