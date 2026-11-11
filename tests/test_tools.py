import sqlite3
import time

import pytest
from hypothesis import given, settings, strategies as st

from heuresis.interfaces import Tool
from heuresis.model import ToolResult
from heuresis.tools import CalcTool, DatesTool, SqlTool, default_tools, run_calls

calc = CalcTool()
dates = DatesTool()
sql = SqlTool()


def c(expr, **kw):
    return calc.run("k1", {"expr": expr, **kw})


def val(expr, **kw):
    r = c(expr, **kw)
    assert r.ok, r.error
    return r.value


# ---------------------------------------------------------------- calc


def test_protocol_and_defaults():
    tools = default_tools()
    assert [t.name for t in tools] == ["calc", "dates", "sql"]
    assert all(isinstance(t, Tool) for t in tools)


def test_decimal_exact():
    assert val("0.1 + 0.2") == "0.3"
    assert val("1200 * 0.06") == "72"
    assert val("10 / 4") == "2.5"
    assert val("1/3").startswith("0.3333")


def test_precedence_and_ops():
    assert val("2 + 3 * 4") == "14"
    assert val("(2 + 3) * 4") == "20"
    assert val("2 ** 3 ** 2") == "512"
    assert val("-2 ** 2") == "-4"
    assert val("7 // 2") == "3"
    assert val("-7 // 2") == "-4"
    assert val("-7 % 3") == "2"
    assert val("7 % -3") == "-2"
    assert val("2 ** -2") == "0.25"
    assert val("-(3 - 5)") == "2"


def test_functions():
    assert val("min(3, 1, 2)") == "1"
    assert val("max([3, 1, 2])") == "3"
    assert val("sum([0.1, 0.2, 0.3])") == "0.6"
    assert val("abs(-4.5)") == "4.5"
    assert val("round(2.675, 2)") == "2.68"
    assert val("round(2.5)") == "3"
    assert val("round(1234.5, -2)") == "1200"


def test_steps_and_result_shape():
    r = c("1 + 2 * 3")
    assert isinstance(r, ToolResult) and r.mark == "k1" and r.tool == "calc"
    assert r.steps[-2:] == ["2 * 3 = 6", "1 + 6 = 7"]


@pytest.mark.parametrize(
    "expr",
    [
        "x + 1",
        "__import__('os')",
        "(1).real",
        "abs.__call__(1)",
        "len([1])",
        "lambda: 1",
        "2 ** 1000",
        "9 ** 9 ** 9",
        "2 ** 0.5",
        "1 / 0",
        "1 // 0",
        "1 % 0",
        "0 ** -1",
        "'a'",
        "True",
        "1j",
        "1e5",
        "[1, 2]",
        "sum(1, 2)",
        "sum([])",
        "round(1, 2, 3)",
        "max()",
        "1 if 1 else 2",
        "1 < 2",
        "not 1",
        "~1",
        "1 &  2",
        "(1, 2)",
        "",
        "1 +",
        "min(key=abs, a=1)",
    ],
)
def test_rejected(expr):
    r = c(expr)
    assert not r.ok and r.error and r.value is None


def test_rejects_non_string_and_bad_locale():
    assert not calc.run("k1", {}).ok
    assert not calc.run("k1", {"expr": 5}).ok
    assert not c("1", locale="fr").ok


def test_percent():
    assert val("5%") == "0.05"
    assert val("1200 * 6%") == "72"
    assert val("100 + 5%") == "100.05"
    assert val("10 % 3") == "1"
    assert val("10%3") == "1"
    assert val("5% * 2") == "0.1"
    assert val("12.5 %") == "0.125"


def test_separators_without_locale_are_rejected():
    for e in ("1,234.56 + 1", "1.234,56 + 1", "1,234 + 1"):
        r = c(e)
        assert not r.ok and "locale" in r.error
    assert val("1_000 + 1") == "1001"
    assert val("max(1,234)") == "234"  # comma is an argument separator here
    assert val("max(1; 2)") == "2"


def test_locales():
    assert val("1,234.56 + 1", locale="en") == "1235.56"
    assert val("1.234,56 + 1", locale="pt") == "1235.56"
    assert val("1.234.567,5", locale="pt") == "1234567.5"
    assert val("2,5 * 2", locale="pt") == "5"
    assert val("max(1,5; 2)", locale="pt") == "2"
    assert val("max(1, 2)", locale="en") == "2"
    assert val("1.234,56 * 10%", locale="pt") == "123.456"
    for e, loc in [
        ("1.234,56", "en"),
        ("1,234.56", "pt"),
        ("12,34,567", "en"),
        ("1,5", "en"),
        ("1.2.3", "en"),
        ("1.2345", "pt"),
    ]:
        assert not c(e, locale=loc).ok, (e, loc)


def test_no_binary_float_leak():
    assert val("0.1 * 3") == "0.3"
    assert val("123456789012345678.123456789") == "123456789012345678.123456789"


@settings(max_examples=200, deadline=None)
@given(
    st.recursive(
        st.integers(0, 50).map(str),
        lambda ch: st.one_of(
            st.tuples(ch, st.sampled_from(["+", "-", "*"]), ch).map(lambda t: f"({t[0]} {t[1]} {t[2]})"),
            ch.map(lambda x: f"-({x})"),
        ),
        max_leaves=8,
    )
)
def test_property_matches_python_integers(expr):
    assert val(expr) == str(eval(expr))


# ---------------------------------------------------------------- dates


def d(**kw):
    return dates.run("k1", kw)


def test_diff_days():
    r = d(op="diff", start="2024-02-28", end="2024-03-01")
    assert r.ok and r.value == 2  # leap year
    assert d(op="diff", start="2023-02-28", end="2023-03-01").value == 1
    assert d(op="diff", start="2024-03-01", end="2024-02-28").value == -2
    assert r.steps


def test_diff_months_years():
    assert d(op="diff", start="2024-01-31", end="2024-02-29", unit="months").value == 1
    assert d(op="diff", start="2024-01-31", end="2024-02-28", unit="months").value == 0
    assert d(op="diff", start="2024-01-15", end="2024-03-14", unit="months").value == 1
    assert d(op="diff", start="2024-01-15", end="2024-03-15", unit="months").value == 2
    assert d(op="diff", start="2024-03-15", end="2024-01-15", unit="months").value == -2
    assert d(op="diff", start="2000-02-29", end="2024-02-29", unit="years").value == 24
    assert d(op="diff", start="2000-02-29", end="2023-02-28", unit="years").value == 23
    assert d(op="diff", start="2000-06-15", end="2024-06-14", unit="years").value == 23


def test_add():
    assert d(op="add", date="2024-01-31", months=1).value == "2024-02-29"
    assert d(op="add", date="2023-01-31", months=1).value == "2023-02-28"
    assert d(op="add", date="2024-02-29", years=1).value == "2025-02-28"
    assert d(op="add", date="2024-02-29", years=4).value == "2028-02-29"
    assert d(op="add", date="2024-03-31", months=-1).value == "2024-02-29"
    assert d(op="add", date="2024-12-31", days=1).value == "2025-01-01"
    assert d(op="add", date="2024-01-31", months=1, days=1).value == "2024-03-01"
    assert d(op="add", date="2024-02-28", days=2).value == "2024-03-01"
    assert d(op="add", date="2024-05-10", years=1, months=-1, days=-10).value == "2025-03-31"


def test_weekday_and_is_before():
    assert d(op="weekday", date="2024-02-29").value == "Thursday"
    assert d(op="weekday", date="2000-01-01").value == "Saturday"
    assert d(op="is_before", a="2024-01-01", b="2024-01-02").value is True
    assert d(op="is_before", a="2024-01-02", b="2024-01-02").value is False
    assert d(op="is_before", a="2024-01-03T10:00:00", b="2024-01-02").value is False


@pytest.mark.parametrize(
    "kw",
    [
        {},
        {"op": "nope"},
        {"op": "diff", "start": "2024-13-01", "end": "2024-01-01"},
        {"op": "diff", "start": "2023-02-29", "end": "2024-01-01"},
        {"op": "diff", "start": "2024-01-01"},
        {"op": "diff", "start": "2024-01-01", "end": "2024-01-02", "unit": "weeks"},
        {"op": "add", "date": "2024-01-01", "days": "x"},
        {"op": "add", "date": "2024-01-01", "days": 1.5},
        {"op": "add", "date": "9999-12-31", "days": 1},
        {"op": "add", "date": "2024-01-01", "years": 10**9},
        {"op": "weekday", "date": 20240101},
    ],
)
def test_dates_errors(kw):
    r = d(**kw)
    assert not r.ok and r.error


# ---------------------------------------------------------------- sql


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "t.sqlite"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT, amount REAL)")
    con.executemany("INSERT INTO t(name, amount) VALUES (?, ?)", [(f"n{i}", i * 1.5) for i in range(120)])
    con.commit()
    con.close()
    return str(p)


def snapshot(path):
    with open(path, "rb") as f:
        return f.read()


def q(db, query, **kw):
    return sql.run("k1", {"db": db, "query": query, **kw})


def test_select(db):
    r = q(db, "SELECT id, name FROM t WHERE id <= 3 ORDER BY id")
    assert r.ok
    assert r.value == {"columns": ["id", "name"], "rows": [[1, "n0"], [2, "n1"], [3, "n2"]], "truncated": False}
    r = q(db, "WITH x AS (SELECT sum(amount) s FROM t) SELECT s FROM x;")
    assert r.ok and r.value["rows"] == [[sum(i * 1.5 for i in range(120))]]


def test_empty_result_is_ok(db):
    r = q(db, "SELECT * FROM t WHERE id < 0")
    assert r.ok and r.value["rows"] == [] and r.value["truncated"] is False
    assert r.value["columns"] == ["id", "name", "amount"]


def test_row_cap(db):
    r = q(db, "SELECT * FROM t")
    assert r.ok and len(r.value["rows"]) == 50 and r.value["truncated"] is True
    r = q(db, "SELECT * FROM t", max_rows=5)
    assert len(r.value["rows"]) == 5 and r.value["truncated"] is True
    r = q(db, "SELECT * FROM t LIMIT 5", max_rows=5)
    assert len(r.value["rows"]) == 5 and r.value["truncated"] is False
    assert not q(db, "SELECT 1", max_rows=0).ok


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO t(name) VALUES ('x')",
        "UPDATE t SET name = 'x'",
        "DELETE FROM t",
        "DROP TABLE t",
        "CREATE TABLE u(a)",
        "ATTACH DATABASE ':memory:' AS m",
        "PRAGMA writable_schema = 1",
        "SELECT 1; DROP TABLE t",
        "SELECT 1; SELECT 2",
        "WITH x AS (SELECT 1) INSERT INTO t(name) SELECT 'a' FROM x",
        "WITH x AS (SELECT 1) DELETE FROM t",
        "VACUUM",
        "",
        "   ",
    ],
)
def test_rejected_and_file_unchanged(db, query):
    before = snapshot(db)
    r = q(db, query)
    assert not r.ok and r.error
    assert snapshot(db) == before
    assert q(db, "SELECT count(*) FROM t").value["rows"] == [[120]]


def test_bad_args(db, tmp_path):
    assert not sql.run("k1", {"query": "SELECT 1"}).ok
    assert not sql.run("k1", {"db": db}).ok
    assert not q(str(tmp_path / "missing.sqlite"), "SELECT 1").ok
    assert not q(db, "SELECT nope FROM t").ok
    assert not q(db, "SELECT 1", timeout_s=-1).ok
    assert not q(str(tmp_path), "SELECT 1").ok


def test_timeout_on_runaway_cte(db):
    t0 = time.monotonic()
    r = q(
        db,
        "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT count(*) FROM c",
        timeout_s=0.3,
    )
    assert not r.ok and "time limit" in r.error
    assert time.monotonic() - t0 < 5


def test_recursive_cte_allowed_when_bounded(db):
    r = q(db, "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c WHERE x < 5) SELECT x FROM c")
    assert r.ok and [row[0] for row in r.value["rows"]] == [1, 2, 3, 4, 5]


# ---------------------------------------------------------------- run_calls


def test_run_calls(db):
    tools = default_tools()
    res = run_calls(
        tools,
        [
            {"mark": "k1", "tool": "calc", "args": {"expr": "2 + 2"}},
            {"mark": "k2", "tool": "dates", "args": {"op": "weekday", "date": "2024-02-29"}},
            {"mark": "k3", "tool": "sql", "args": {"db": db, "query": "SELECT count(*) FROM t"}},
            {"mark": "k4", "tool": "nope", "args": {}},
            {"mark": "k5", "tool": "calc", "args": "bad"},
            {"mark": "k6", "tool": "calc"},
            "garbage",
            {"mark": "k8", "tool": "calc", "args": {"expr": "1/0"}},
        ],
    )
    assert [r.mark for r in res] == ["k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8"]
    assert [r.ok for r in res] == [True, True, True, False, False, False, False, False]
    assert res[0].value == "4" and res[1].value == "Thursday" and res[2].value["rows"] == [[120]]
    assert "unknown tool" in res[3].error


def test_run_calls_survives_a_raising_tool():
    class Boom:
        name = "boom"
        description = ""

        def run(self, mark, args):
            raise RuntimeError("x")

    res = run_calls([Boom()], [{"mark": "k1", "tool": "boom", "args": {}}])
    assert not res[0].ok and res[0].error
    assert run_calls([], []) == []
