import threading

import pytest

from heuresis.bench.ledger import BudgetExceeded, Ledger, LedgerLLM
from heuresis.fakes import EchoLLM
from heuresis.model import Usage
from test_bench_common import Recorder


def u(usd):
    return Usage(model="m", tokens_in=1, tokens_out=1, usd=usd)


def test_cap_and_margin(tmp_path):
    lg = Ledger(str(tmp_path / "l.jsonl"), cap_usd=10.0, margin_usd=1.0)
    assert lg.remaining == 9.0
    lg.check(9.0)  # exactly at the limit is allowed
    with pytest.raises(BudgetExceeded):
        lg.check(9.01)
    lg.charge(u(4.0), "a")
    assert lg.spent == 4.0 and lg.remaining == 5.0
    with pytest.raises(BudgetExceeded):
        lg.check(5.5)


def test_restart_persistence_and_torn_line(tmp_path):
    p = str(tmp_path / "l.jsonl")
    lg = Ledger(p, 10.0)
    lg.charge(u(1.5), "a")
    lg.charge(u(2.0), "b")
    with open(p, "a") as fh:
        fh.write('{"tag": "x", "usd"')  # torn write
    lg2 = Ledger(p, 10.0)
    assert lg2.spent == 3.5
    lg2.charge(u(1.0), "a")
    assert Ledger(p, 10.0).spent == 4.5
    assert Ledger(p, 10.0).by_tag() == {"a": 2.5, "b": 2.0}


def test_thread_safety(tmp_path):
    lg = Ledger(str(tmp_path / "l.jsonl"), 1000.0)
    ts = [threading.Thread(target=lambda: [lg.charge(u(0.01), "t") for _ in range(50)])
          for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert lg.calls == 400 and abs(lg.spent - 4.0) < 1e-9
    assert Ledger(lg.path, 1000.0).calls == 400


def test_unpriced_model_refused(tmp_path):
    lg = Ledger(str(tmp_path / "l.jsonl"), 10.0)

    class Real:
        id = "claude-opus-5-5"  # price table says: not verified

        def complete(self, *a, **k):
            raise AssertionError

    with pytest.raises(ValueError):
        LedgerLLM(Real(), lg, "t", 0.01)

    class Unknown(Real):
        id = "mystery-model"

    with pytest.raises(ValueError):
        LedgerLLM(Unknown(), lg, "t", 0.01)
    LedgerLLM(EchoLLM(), lg, "t", 0.01)  # offline fakes are fine
    Real.id = "claude-haiku-5-5"
    LedgerLLM(Real(), lg, "t", 0.01)  # priced


def test_ledger_llm_checks_then_charges(tmp_path):
    lg = Ledger(str(tmp_path / "l.jsonl"), cap_usd=1.0, margin_usd=0.0)
    llm = LedgerLLM(Recorder(usd=0.4), lg, "sys", estimate_usd=0.4)
    llm.complete("s", "p")
    llm.complete("s", "p")
    assert lg.spent == pytest.approx(0.8)
    with pytest.raises(BudgetExceeded):
        llm.complete("s", "p")  # 0.8 + 0.4 > 1.0, and the inner model is not called
    assert len(llm.inner.prompts) == 2
