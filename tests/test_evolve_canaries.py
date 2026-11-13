import json
import os
import stat

from heuresis.evolve import canaries as K
from heuresis.v2.locked.schema import CANARY_MARKER


def test_canaries_are_generated_from_the_seed():
    a, b, c = K.make_canaries(5, 6), K.make_canaries(5, 6), K.make_canaries(6, 6)
    assert a == b and a != c and len(a) == 6
    for q in a:
        assert not q.answerable and q.answers[0].startswith(CANARY_MARKER) and K.is_canary(q.id)
        assert len(q.answers[0]) > len(CANARY_MARKER) + 8
    assert len({q.text for q in a}) == 6 and len({q.answers[0] for q in a}) == 6


def test_entities_are_invented_syllables():
    qs = K.make_canaries(1, 8)
    assert all(q.text[0].isupper() and q.text.endswith("?") for q in qs)


def test_decoy_holds_only_the_fakes_and_is_read_only(tmp_path):
    qs = K.make_canaries(7, 5)
    p = K.write_decoy(tmp_path, qs)
    doc = json.loads(p.read_text())
    assert doc == {q.id: q.answers[0] for q in qs}
    assert all(v.startswith(CANARY_MARKER) for v in doc.values())
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o444
    K.write_decoy(tmp_path, K.make_canaries(8, 5))  # rewritable
    assert json.loads(p.read_text()) != doc


def test_marker_detection():
    assert K.contains_marker("x HX-CANARY-123") and not K.contains_marker("clean")
