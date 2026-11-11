"""CLI end to end against the synthetic legal_br fixture. Offline; no network."""
import json
import sys
from pathlib import Path

import pytest

from heuresis.cli import main

FIXTURE = str(Path(__file__).parent / "fixtures" / "domains" / "legal_br")
ART2 = "urn:lex:br:federal:lei:2020-03-10;1!art2"
Q = "Qual o texto do art. 2º?"


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "corpus.db")
    assert main(["init", path, "--domain", "legal_br"]) == 0
    assert main(["ingest", path, FIXTURE, "--domain", "legal_br"]) == 0
    assert main(["index", path]) == 0
    return path


def run_json(capsys, *argv):
    capsys.readouterr()
    code = main([*argv, "--json"])
    cap = capsys.readouterr()
    return code, json.loads(cap.out), cap.err


def test_init_ingest_index_json(tmp_path, capsys):
    path = str(tmp_path / "c.db")
    assert run_json(capsys, "init", path, "--domain", "legal_br")[0] == 0
    code, data, _ = run_json(capsys, "ingest", path, FIXTURE)  # domain remembered from init
    assert code == 0 and data["counts"]["units"] == 3
    code, data, _ = run_json(capsys, "index", path)
    assert code == 0 and data["embedded"] > 0


def test_ask_two_dates_differ(db, capsys):
    c1, early, err = run_json(capsys, "ask", db, Q, "--as-of", "2021-01-01")
    c2, late, _ = run_json(capsys, "ask", db, Q, "--as-of", "2023-01-01")
    assert c1 == c2 == 0
    assert early["offline"] is True and late["offline"] is True
    assert early["status"] == "answered" and late["status"] == "answered"
    cite = lambda d: [(c["unit_id"], c["valid_from"], c["valid_to"]) for cl in d["claims"] for c in cl["citations"]]  # noqa: E731
    assert cite(early) != cite(late)
    assert cite(early)[0][2] == "2022-06-01" and cite(late)[0][1] == "2022-06-01"
    assert early["usd"] == 0.0


def test_ask_text_notice_and_trace(db, capsys):
    capsys.readouterr()
    assert main(["ask", db, Q, "--as-of", "2021-01-01", "--trace"]) == 0
    cap = capsys.readouterr()
    assert "offline" in cap.err
    assert "status: answered" in cap.out
    assert f"{ART2} @ 2020-03-10..2022-06-01" in cap.out
    assert "grade:" in cap.out and "cost:" in cap.out
    for col in ("stage", "ms", "tokens", "usd", "note"):
        assert col in cap.out
    assert "understand" in cap.out and "verify" in cap.out


def test_ask_abstains_before_corpus_begins(db, capsys):
    code, data, _ = run_json(capsys, "ask", db, Q, "--as-of", "2000-01-01")
    assert code == 0 and data["status"] == "abstained"
    assert data["abstention"]["type"] in ("not_valid_at_date", "no_source")


def test_ask_source_filter(db, capsys):
    code, data, _ = run_json(capsys, "ask", db, Q, "--as-of", "2023-01-01", "--source", "no-such-source")
    assert code == 0 and data["status"] == "abstained"


def test_model_without_budget_refused(db, capsys):
    capsys.readouterr()
    assert main(["ask", db, Q, "--model", "claude-haiku-5-5"]) == 2
    assert "--budget" in capsys.readouterr().err


def test_budget_without_model_refused(db, capsys):
    assert main(["ask", db, Q, "--budget", "1"]) == 2


def test_bad_date_is_a_usage_error(db):
    with pytest.raises(SystemExit) as e:
        main(["ask", db, Q, "--as-of", "yesterday"])
    assert e.value.code == 2


def test_search_respects_date(db, capsys):
    code, data, _ = run_json(capsys, "search", db, "texto sintético", "--as-of", "2021-01-01", "-k", "5")
    assert code == 0 and data["passages"]
    for p in data["passages"]:
        assert (p["valid_from"] or "") <= "2021-01-01" and (p["valid_to"] is None or p["valid_to"] > "2021-01-01")
    capsys.readouterr()
    assert main(["search", db, "texto sintético", "--as-of", "2021-01-01"]) == 0
    assert "@" in capsys.readouterr().out


def test_unit_at_two_dates(db, capsys):
    _, early, _ = run_json(capsys, "unit", db, ART2, "--as-of", "2021-01-01")
    _, late, _ = run_json(capsys, "unit", db, ART2, "--as-of", "2023-06-01")
    assert "alfa" in early["text"] and "beta" in late["text"]
    assert early["valid_to"] == late["valid_from"] == "2022-06-01"
    assert main(["unit", db, "nope", "--as-of", "2023-06-01"]) == 2


def test_verify_against_unit(db, capsys):
    code, ok, _ = run_json(capsys, "verify", db, "--text", "Texto sintético beta, nova redação corrigida.",
                           "--unit", ART2, "--as-of", "2023-06-01")
    assert code == 0 and ok["claims"][0]["label"] == "supported"
    assert ok["claims"][0]["citations"][0]["unit_id"] == ART2
    code, bad, _ = run_json(capsys, "verify", db, "--text", "Texto sintético beta, nova redação corrigida.",
                            "--unit", ART2, "--as-of", "2021-01-01")
    assert bad["claims"][0]["support"] < ok["claims"][0]["support"]  # the older wording supports it less
    capsys.readouterr()
    assert main(["verify", db, "--text", "x.", "--unit", "nope"]) == 2


def test_hash(capsys):
    code, data, _ = run_json(capsys, "hash")
    assert code == 0 and len(data["locked"]) == 64 and len(data["surface"]) == 64
    from heuresis.locked import locked_hash

    assert data["locked"] == locked_hash()


def test_bench_requires_cap_for_paid(capsys):
    try:
        import heuresis.bench.run  # noqa: F401
    except ImportError:
        assert main(["bench", "run"]) == 2
        assert "not available" in capsys.readouterr().err
    else:
        assert main(["bench", "run", "--paid"]) == 2


def test_missing_database(tmp_path, capsys):
    assert main(["search", str(tmp_path / "none.db"), "x"]) == 2
    assert "does not exist" in capsys.readouterr().err
