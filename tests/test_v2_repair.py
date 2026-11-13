"""The text of a repair turn."""
from __future__ import annotations

from heuresis.model import Claim
from heuresis.v2.locked.judge import Verdict
from heuresis.v2.repair import feedback

OK = {"exists": True, "valid_at_date": True, "numbers_traced": True, "references_traced": True}


def claim(text, marks=(), note="", kind="cited", **bad):
    checks = {**OK, **{k: False for k in bad}}
    return Claim(text=text, passage_marks=list(marks), checks=checks, note=note, kind=kind)


def test_nothing_failed_is_empty():
    assert feedback([claim("Fine.", ["t1"])]) == ""
    assert feedback([]) == ""


def test_failed_sentences_with_reasons_and_previous_answer():
    cs = [claim("Good sentence.", ["t1"]),
          claim("No mark here.", [], exists=False, kind="derived"),
          claim("Wrong number 77.", ["t2"], note="number not in the cited passages: 77",
                numbers_traced=False),
          claim("Old rule.", ["t3"], valid_at_date=False)]
    fb = feedback(cs)
    assert fb.startswith("Your previous answer:")
    assert "- Good sentence. [t1]" in fb and "- Wrong number 77. [t2]" in fb
    failed = fb.split("Failed sentences:")[1]
    assert '"Good sentence."' not in failed
    assert '"No mark here.": ' in failed
    assert "number not in the cited passages: 77" in failed
    assert "not in force at the date" in failed


def test_verdict_sentences_are_listed_among_the_judged_only():
    cs = [claim("Gate fail.", ["t1"], valid_at_date=False),
          claim("Judged one.", ["t2"]), claim("Judged two.", ["t3"])]
    v = Verdict(sentences={0: "NOT_SUPPORTED", 1: "SUPPORTED"}, readable=True)
    fb = feedback(cs, v)
    assert '"Judged one.": the cited passages do not state this' in fb
    assert '"Judged two.": ' not in fb and '"Gate fail.": ' in fb
