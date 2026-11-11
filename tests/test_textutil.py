import shutil
from pathlib import Path

import pytest

from heuresis import AsOf, Engine, Scope
from heuresis.textutil import split_sentences

FIX = Path(__file__).parent / "fixtures" / "domains" / "legal_br"
ART2 = "urn:lex:br:federal:lei:2020-03-10;1!art2"


def test_regression_passage_two_sentences():
    text = "Art. 2º O limite é de R$ 4.800.000,00 por ano. Vigora desde 2018."
    assert split_sentences(text) == [
        "Art. 2º O limite é de R$ 4.800.000,00 por ano.", "Vigora desde 2018."]


@pytest.mark.parametrize("text", [
    "Ver art. 5 da lei. Fim.",
    "Ver arts. 5 e 6 da lei. Fim.",
    "Ver Art. 5 da lei. Fim.",
    "Conforme n. 5 da lista. Fim.",
    "Conforme nº. 5 da lista. Fim.",
    "Conforme no. 5 da lista. Fim.",
    "A Acme Inc. Brasil vendeu tudo. Fim.",
    "Ver par. 3 do texto. Fim.",
    "Silva et al. mostraram isso. Fim.",
    "Veja cf. a norma citada. Fim.",
    "Algo, e.g. um caso. Fim.",
    "Algo, i.e. um caso. Fim.",
    "Frutas, etc. e legumes. Fim.",
    "A contra B vs. C no caso. Fim.",
    "O Dr. Silva chegou. Fim.",
    "O Sr. Silva chegou. Fim.",
    "A Sra. Silva chegou. Fim.",
    "Mr. Smith left. Fim.",
    "Mrs. Smith left. Fim.",
    "Ms. Smith left. Fim.",
    "St. Louis is far. Fim.",
    "Nos U.S. houve isso. Fim.",
    "Falou J. Smith ontem. Fim.",
    "A taxa é 4.8 por cento. Fim.",
    "O valor é 1.200 reais. Fim.",
    "Conforme o 2º. e o 3º. itens. Fim.",
    "Conforme o § 5º trata disso. Fim.",
])
def test_no_split_inside_abbreviation(text):
    parts = split_sentences(text)
    assert len(parts) == 2, parts
    assert parts[1] == "Fim."


def test_real_boundaries_and_marks():
    assert split_sentences("Frutas, etc. Depois veio outra. Sim?") == [
        "Frutas, etc.", "Depois veio outra.", "Sim?"]
    assert split_sentences("A [t1]. B [t2][t3]. C") == ["A [t1].", "B [t2][t3].", "C"]
    assert split_sentences("") == []


def test_engine_echo_returns_full_first_sentence(tmp_path):
    src = tmp_path / "legal"
    shutil.copytree(FIX, src)
    ev = src / "events.jsonl"
    new = "Art. 2º O limite é de R$ 4.800.000,00 por ano. Vigora desde 2018."
    lines = []
    for ln in ev.read_text().splitlines():
        if '"unit_id": "%s"' % ART2 in ln and '"text"' in ln:
            import json
            d = json.loads(ln)
            d["text"] = new
            ln = json.dumps(d)
        lines.append(ln)
    ev.write_text("\n".join(lines) + "\n")
    e = Engine.open(str(tmp_path / "l.db"), "legal_br")
    try:
        e.ingest(str(src))
        a = e.ask("limite por ano", as_of=AsOf(valid="2023-03-01"), scope=Scope(unit_prefix=ART2))
    finally:
        e.close()
    assert "R$ 4.800.000,00 por ano" in a.text, a.text
    assert "Vigora" not in a.text
