"""Shared helpers for the bench tests (no tests here)."""
import json

from heuresis.bench.types import Dataset, Question
from heuresis.model import Usage

UNITS = {
    "u1": [("2018-01-01", "The Alpha Treaty set the customs limit at 500 euros."),
           ("2022-01-01", "The Alpha Treaty set the customs limit at 800 euros.")],
    "u2": [("2018-01-01", "The Beta river is 120 kilometres long.")],
    "u3": [("2018-01-01", "Gamma city was founded in 1850 by settlers.")],
    "u4": [("2018-01-01", "The Delta bridge opened in 1990.")],
    "u5": [("2018-01-01", "The Epsilon school has 300 pupils.")],
    "u6": [("2018-01-01", "The Zeta lake has a depth of 40 metres.")],
    "u7": [("2018-01-01", "The Eta railway runs between Gamma and Delta.")],
    "u8": [("2018-01-01", "The Theta museum closes on Mondays.")],
}


def write_corpus(path):
    path.mkdir(parents=True, exist_ok=True)
    units, events = [], []
    for uid, versions in UNITS.items():
        units.append({"id": uid, "source_id": "s", "title": uid})
        for i, (date, text) in enumerate(versions):
            events.append({"id": f"{uid}-e{i}", "unit_id": uid,
                           "op": "create" if i == 0 else "replace", "date": date, "text": text,
                           "recorded_at": date})
    (path / "units.jsonl").write_text("\n".join(json.dumps(u) for u in units) + "\n")
    (path / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return str(path)


def questions():
    qs = [
        Question("q01", "How long is the Beta river?", ("120 kilometres",), gold_units=("u2",), cluster="a"),
        Question("q02", "When was Gamma city founded?", ("1850",), gold_units=("u3",), cluster="a"),
        Question("q03", "When did the Delta bridge open?", ("1990",), gold_units=("u4",), cluster="b"),
        Question("q04", "How many pupils does the Epsilon school have?", ("300",), gold_units=("u5",), cluster="b"),
        Question("q05", "What is the depth of the Zeta lake?", ("40 metres",), gold_units=("u6",), cluster="c"),
        Question("q06", "Where does the Eta railway run?", ("Gamma and Delta",), gold_units=("u7",), cluster="c"),
        Question("q07", "What was the Alpha Treaty customs limit?", ("500 euros",), as_of="2019-06-01",
                 gold_units=("u1",), cluster="d", kind="temporal"),
        Question("q08", "What was the Alpha Treaty customs limit?", ("800 euros",), as_of="2023-06-01",
                 gold_units=("u1",), cluster="d", kind="temporal"),
        Question("q09", "Who painted the Omega fresco?", (), answerable=False, cluster="e"),
        Question("q10", "What is the population of Sigma?", (), answerable=False, cluster="e"),
        Question("q11", "When does the Theta museum close?", ("Mondays",), gold_units=("u8",), cluster="f"),
        Question("q12", "Which colour is the Kappa flag?", (), answerable=False, cluster="f"),
    ]
    return tuple(qs)


def make_dataset(tmp_path, corpus_tokens=120):
    corpus = write_corpus(tmp_path / "corpus")
    return Dataset(name="tiny", corpus_dir=corpus,
                   questions={"dev": questions(), "test": questions()[:4],
                              "dev2": questions()[2:9]},
                   licence="test", corpus_tokens=corpus_tokens, meta={})


class Recorder:
    """Offline LLM that records prompts and replies from a function."""

    id = "recorder"
    offline = True

    def __init__(self, reply=None, usd=0.0):
        self.reply = reply or (lambda system, prompt: "ABSTAIN\nCONFIDENCE: 10")
        self.usd = usd
        self.prompts = []
        self.systems = []

    def complete(self, system, prompt, *, max_tokens=600):
        self.prompts.append(prompt)
        self.systems.append(system)
        text = self.reply(system, prompt)
        return text, Usage(model=self.id, tokens_in=len(prompt.split()),
                           tokens_out=len(text.split()), usd=self.usd)
