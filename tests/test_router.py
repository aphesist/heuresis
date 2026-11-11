import pytest

from heuresis.fakes import HashEmbedder
from heuresis.model import AsOf, Scope
from heuresis.router import NearestIntent, understand
from heuresis.surface.config import RouterCfg

TODAY = "2025-06-10"


def run(text, **kw):
    kw.setdefault("cfg", RouterCfg())
    kw.setdefault("today", TODAY)
    return understand(text, **kw)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("What was the rate on 2024-03-15?", "2024-03-15"),
        ("What was the rate on 15/03/2024?", "2024-03-15"),
        ("What was the rate in March 2024?", "2024-03-31"),
        ("Rate for February 2024", "2024-02-29"),
        ("Qual era a alíquota em março de 2024?", "2024-03-31"),
        ("Qual era a alíquota março/2024?", "2024-03-31"),
        ("Qual era a alíquota em marco de 2024?", "2024-03-31"),
        ("What happened in 2019?", "2019-12-31"),
        ("O que mudou em 2019?", "2019-12-31"),
        ("What is the rule today?", TODAY),
        ("Qual é a regra hoje?", TODAY),
    ],
)
def test_date_forms(text, expected):
    q = run(text)
    assert q.as_of.valid == expected
    assert q.dated is True


def test_no_date_and_invalid_date():
    q = run("What is the policy?")
    assert q.as_of.valid is None and q.dated is False
    assert run("on 31/02/2024 what applied?").as_of.valid is None


def test_first_date_wins():
    assert run("From 2020-01-01 to 2021-01-01").as_of.valid == "2020-01-01"


def test_caller_as_of_wins():
    given = AsOf(valid="2010-01-01", recorded="2011-01-01")
    q = run("What was the rate in March 2024?", as_of=given)
    assert q.as_of == given
    assert q.dated is False


def test_caller_rule_sets_fields_and_runs_first():
    def rule(text):
        return {"intent": "table", "scope": Scope(kinds=("schema",))}

    q = run("how much is the total?", rules=[rule])
    # caller rule says table, built-in says compute: collision, no classifier,
    # caller rule fired first so it wins.
    assert q.intent == "table"
    assert q.scope.kinds == ("schema",)
    assert q.decided_by == "rules"


def test_caller_rule_bad_output_ignored():
    def boom(text):
        raise RuntimeError("x")

    q = run("hello?", rules=[boom, lambda t: "nonsense", lambda t: {"zzz": 1}])
    assert q.intent == "out_of_scope"


@pytest.mark.parametrize(
    "text",
    [
        "What is 1200 * 0.06?",
        "How much was the total fee?",
        "How many rules were repealed?",
        "Calculate the sum of the fines",
        "What is the average penalty?",
        "What percent applies?",
        "Quanto é o imposto devido?",
        "Calcule a multa",
    ],
)
def test_compute(text):
    q = run(text)
    assert (q.intent, q.decided_by, q.confidence) == ("compute", "rules", 1.0)


def test_dates_do_not_trigger_compute():
    assert run("Rule on 15/03/2024").intent == "lookup"
    assert run("Rule on 2024-03-15").intent == "lookup"


@pytest.mark.parametrize(
    "text",
    [
        "What is the capital of the country that signed the treaty?",
        "Who signed the amendment of the contract?",
        "Compare the notice period of plan A and plan B",
        "What is the difference between article 5 and article 9?",
        "Qual o prazo da lei que revogou o decreto?",
        "Compare o artigo 5 com o artigo 9",
    ],
)
def test_multi_hop(text):
    q = run(text)
    assert (q.intent, q.decided_by) == ("multi_hop", "rules")


def test_table_needs_schema_kind():
    text = "Which column in the customers table holds the tax id?"
    assert run(text).intent == "lookup"
    q = run(text, scope=Scope(kinds=("schema",)))
    assert (q.intent, q.decided_by) == ("table", "rules")
    q2 = run("Quais colunas tem a tabela clientes?", scope=Scope(kinds=("schema", "text")))
    assert q2.intent == "table"


@pytest.mark.parametrize("text", ["", "   ", "hi", "Hello!", "Olá, bom dia", "obrigado", "???", "thanks"])
def test_out_of_scope(text):
    q = run(text)
    assert (q.intent, q.decided_by) == ("out_of_scope", "rules")


def test_odd_input_never_raises():
    for bad in (None, 123, "\x00\x01", "é" * 5000, "9" * 5000, "0/0/0000"):
        q = run(bad)
        assert q.intent in ("lookup", "compute", "out_of_scope")
    q = understand("x", cfg=RouterCfg(), classifier=lambda t: 1 / 0)
    assert q.intent == "lookup" and q.decided_by == "default"
    q = understand("x", cfg=RouterCfg(), classifier=lambda t: ("bogus", 0.9))
    assert q.intent == "lookup"


def test_default_without_classifier_or_rule():
    q = run("What does section 4 say about notice?")
    assert (q.intent, q.confidence, q.decided_by, q.clarify) == ("lookup", 1.0, "default", None)


def test_default_intent_from_cfg():
    q = run("What does section 4 say?", cfg=RouterCfg(default_intent="multi_hop"))
    assert q.intent == "multi_hop" and q.decided_by == "default"


def test_classifier_runs_when_no_rule_fired():
    calls = []

    def clf(text):
        calls.append(text)
        return ("multi_hop", 0.9)

    q = run("What does section 4 say?", classifier=clf)
    assert calls and (q.intent, q.decided_by, q.confidence) == ("multi_hop", "classifier", 0.9)


def test_classifier_skipped_when_single_rule_fired():
    def clf(text):
        raise AssertionError("must not run")

    q = run("How much is the total?", classifier=clf)
    assert q.intent == "compute" and q.decided_by == "rules"


def test_rule_collision_goes_to_classifier():
    text = "How much is the capital of the country that signed the treaty?"
    assert run(text).intent == "compute"  # no classifier: first rule wins
    q = run(text, classifier=lambda t: ("multi_hop", 0.95))
    assert (q.intent, q.decided_by) == ("multi_hop", "classifier")


def test_ask_back_below_threshold():
    q = run("What does section 4 say?", classifier=lambda t: ("compute", 0.3))
    assert q.intent == "lookup"  # default_intent, never a silent guess
    assert q.decided_by == "classifier" and q.confidence == 0.3
    assert q.clarify and q.clarify.endswith("?") and "calculation" in q.clarify
    assert "lookup" in q.clarify or "direct lookup" in q.clarify


def test_no_ask_back_at_or_above_threshold():
    q = run("What does section 4 say?", classifier=lambda t: ("compute", 0.6))
    assert q.clarify is None and q.intent == "compute"
    q = run("What does section 4 say?", classifier=lambda t: ("compute", 0.61),
            cfg=RouterCfg(ask_threshold=0.9))
    assert q.clarify is not None and q.intent == "lookup"


def test_ask_back_offers_two_most_likely_for_collision():
    text = "How much is the capital of the country that signed the treaty?"
    q = run(text, classifier=lambda t: ("table", 0.1))
    assert q.clarify and q.intent == "lookup"


EXAMPLES = [
    ("what does the contract say about notice", "lookup"),
    ("what is the notice period in the lease", "lookup"),
    ("total cost of the fees summed over the year", "compute"),
    ("calculate the sum of the penalties", "compute"),
    ("who wrote the report that cites the amendment", "multi_hop"),
    ("compare the clauses of the two contracts", "multi_hop"),
]


def test_nearest_intent_basic():
    nn = NearestIntent(HashEmbedder(), EXAMPLES)
    label, conf = nn("what does the lease say about notice")
    assert label == "lookup" and 0.0 <= conf <= 1.0
    label, conf = nn("calculate the sum of the fees")
    assert label == "compute"
    assert nn.ranked("calculate the sum of the fees")[0][0] == "compute"


def test_nearest_intent_confidence_reflects_margin():
    nn = NearestIntent(HashEmbedder(), EXAMPLES)
    _, exact = nn("calculate the sum of the penalties")  # identical to an example
    _, vague = nn("zzz qqq")
    assert exact > vague
    assert 0.0 <= vague <= 1.0 and 0.0 <= exact <= 1.0


def test_nearest_intent_swapped_pairs_and_empty():
    nn = NearestIntent(HashEmbedder(), [(l, t) for t, l in EXAMPLES])
    assert nn("calculate the sum of the penalties")[0] == "compute"
    empty = NearestIntent(HashEmbedder(), [])
    assert empty("anything") == ("lookup", 0.0)


def test_nearest_intent_as_classifier_with_ask_back():
    nn = NearestIntent(HashEmbedder(), EXAMPLES)
    q = run("zzz qqq", classifier=nn, cfg=RouterCfg(ask_threshold=1.01))
    assert q.clarify and q.intent == "lookup" and q.decided_by == "classifier"
    q = run("calculate the sum of the penalties", classifier=nn,
            cfg=RouterCfg(ask_threshold=0.0))
    assert q.intent == "compute" and q.clarify is None


def test_determinism():
    nn = NearestIntent(HashEmbedder(), EXAMPLES)
    kw = dict(cfg=RouterCfg(), classifier=nn, today=TODAY)
    a = understand("what about March 2024 notice", **kw)
    b = understand("what about March 2024 notice", **kw)
    assert a == b
    nn2 = NearestIntent(HashEmbedder(), EXAMPLES)
    assert nn("some text here") == nn2("some text here")
