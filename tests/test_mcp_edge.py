"""MCP edge: in-process through the line handler, and once through a real subprocess."""
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from heuresis import mcp_edge as m
from heuresis.cli import main as cli_main

FIXTURE = str(Path(__file__).parent / "fixtures" / "domains" / "legal_br")
ART2 = "urn:lex:br:federal:lei:2020-03-10;1!art2"
META = {m.META_VERSION: m.MODERN_VERSION, m.META_CLIENT_CAPS: {}}


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("mcp") / "c.db")
    assert cli_main(["init", path, "--domain", "legal_br"]) == 0
    assert cli_main(["ingest", path, FIXTURE]) == 0
    assert cli_main(["index", path]) == 0
    return path


@pytest.fixture()
def edge(db):
    e = m.McpEdge(db)
    yield e
    e.close()


def rpc(edge, method, params=None, id=1, meta=True):
    p = dict(params or {})
    if meta:
        p["_meta"] = META
    out = edge.handle_line(json.dumps({"jsonrpc": "2.0", "id": id, "method": method, "params": p}))
    return json.loads(out)


def call(edge, name, args):
    r = rpc(edge, "tools/call", {"name": name, "arguments": args})
    return r["result"]


def test_discover(edge):
    r = rpc(edge, "server/discover")["result"]
    assert r["supportedVersions"] == ["2026-07-28"] and r["resultType"] == "complete"
    assert r["_meta"][m.META_SERVER_INFO]["name"] == "heuresis"


def test_tools_list_hides_ingest_by_default(db):
    names = lambda e: [t["name"] for t in rpc(e, "tools/list")["result"]["tools"]]  # noqa: E731
    assert names(m.McpEdge(db)) == ["ask", "search", "verify", "get_unit"]
    assert names(m.McpEdge(db, allow_ingest=True)) == ["ask", "search", "verify", "get_unit", "ingest"]


def test_schemas_are_strict(db):
    for t in rpc(m.McpEdge(db, allow_ingest=True), "tools/list")["result"]["tools"]:
        s = t["inputSchema"]
        assert s["additionalProperties"] is False and s["type"] == "object"
        for name, prop in s["properties"].items():
            if prop["type"] == "string":
                assert "maxLength" in prop, (t["name"], name)
            if prop["type"] == "array":
                assert "maxItems" in prop, (t["name"], name)


def test_ingest_hidden_tool_is_unknown(edge):
    r = rpc(edge, "tools/call", {"name": "ingest", "arguments": {"path": FIXTURE}})
    assert r["error"]["code"] == m.INVALID_PARAMS


def test_ask_happy(edge):
    r = call(edge, "ask", {"question": "Qual o texto do art. 2º?", "as_of": "2023-01-01"})
    assert r["isError"] is False
    d = r["structuredContent"]
    assert d["status"] == "answered" and d["claims"][0]["citations"][0]["valid_from"] == "2022-06-01"
    assert json.loads(r["content"][0]["text"]) == d
    assert "server_budget" not in d


def test_ask_validation(edge):
    for args in ({}, {"question": ""}, {"question": "x", "as_of": "2023-13-45"}, {"question": "x", "as_of": "ontem"},
                 {"question": "x", "extra": 1}, {"question": "x", "budget_usd": -1}, {"question": "x", "sources": "a"},
                 {"question": "x" * 5000}, {"question": "x\x00y"}, {"question": "x", "recorded": "nope"}):
        r = call(edge, "ask", args)
        assert r["isError"] is True and r["structuredContent"]["error"]["kind"] == "InvalidArguments", args


def test_search(edge):
    r = call(edge, "search", {"question": "texto sintético", "as_of": "2021-01-01", "k": 3})
    assert r["isError"] is False and 0 < len(r["structuredContent"]["passages"]) <= 3
    for k in (0, 51, "3", True):
        assert call(edge, "search", {"question": "x", "k": k})["isError"] is True


def test_get_unit(edge):
    r = call(edge, "get_unit", {"unit_id": ART2, "as_of": "2021-01-01"})
    assert "alfa" in r["structuredContent"]["unit"]["text"]
    r = call(edge, "get_unit", {"unit_id": ART2, "as_of": "2023-01-01"})
    assert "beta" in r["structuredContent"]["unit"]["text"]
    r = call(edge, "get_unit", {"unit_id": "nope"})
    assert r["isError"] and r["structuredContent"]["error"]["kind"] == "NotFound"
    assert call(edge, "get_unit", {})["isError"] is True


def test_verify(edge):
    r = call(edge, "verify", {"text": "Texto sintético beta, nova redação corrigida.", "unit_ids": [ART2], "as_of": "2023-06-01"})
    assert r["isError"] is False and r["structuredContent"]["claims"][0]["label"] == "supported"
    assert call(edge, "verify", {"text": "x", "unit_ids": []})["isError"] is True
    assert call(edge, "verify", {"text": "x", "unit_ids": ["a"] * 40})["isError"] is True
    r = call(edge, "verify", {"text": "x.", "unit_ids": ["nope"]})
    assert r["isError"] and r["structuredContent"]["error"]["kind"] == "NotFound"


def test_ingest_tool(tmp_path):
    path = str(tmp_path / "fresh.db")
    e = m.McpEdge(path, domain="legal_br", allow_ingest=True)
    try:
        r = call(e, "ingest", {"path": FIXTURE})
        assert r["isError"] is False and r["structuredContent"]["counts"]["units"] == 3
        assert call(e, "get_unit", {"unit_id": ART2, "as_of": "2021-01-01"})["isError"] is False
        assert call(e, "ingest", {"path": str(tmp_path / "missing")})["structuredContent"]["error"]["kind"] == "NotFound"
        assert call(e, "ingest", {"path": FIXTURE, "domain": "nope"})["isError"] is True
        assert call(e, "ingest", {"path": FIXTURE, "x": 1})["isError"] is True
    finally:
        e.close()


def test_budget_shared_cap(db):
    class Spender:
        id = "spender"

        def complete(self, system, prompt, *, max_tokens=600):
            from heuresis.fakes import EchoLLM
            from heuresis.model import Usage

            text, _ = EchoLLM().complete(system, prompt)
            return text, Usage(model="spender", tokens_in=1, tokens_out=1, usd=0.6)

    from heuresis.llm import BudgetedLLM

    e = m.McpEdge(db, model="m", budget_usd=1.0, llm=BudgetedLLM(Spender(), 1.0))
    try:
        q = {"question": "Qual o texto do art. 2º?", "as_of": "2023-01-01"}
        r1 = call(e, "ask", q)["structuredContent"]
        assert r1["server_budget"]["spent_usd"] == pytest.approx(0.6)
        call(e, "ask", q)
        r3 = call(e, "ask", q)
        assert r3["isError"] and r3["structuredContent"]["error"]["kind"] == "BudgetExhausted"
    finally:
        e.close()


def test_model_requires_budget(db):
    with pytest.raises(ValueError):
        m.McpEdge(db, model="x")
    assert m.main(["--db", db, "--model", "x"]) == 2


def test_legacy_handshake(edge):
    r = rpc(edge, "tools/list", meta=False)
    assert r["error"]["code"] == m.INVALID_PARAMS
    r = rpc(edge, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}}, meta=False)["result"]
    assert r["protocolVersion"] == "2025-06-18" and r["serverInfo"]["name"] == "heuresis"
    assert edge.handle_line(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})) is None
    assert rpc(edge, "ping", meta=False)["result"] == {}
    names = [t["name"] for t in rpc(edge, "tools/list", meta=False)["result"]["tools"]]
    assert "ask" in names
    r = rpc(edge, "tools/call", {"name": "get_unit", "arguments": {"unit_id": ART2, "as_of": "2021-01-01"}}, meta=False)
    assert r["result"]["isError"] is False
    r = rpc(edge, "initialize", {"protocolVersion": "1999-01-01"}, meta=False)["result"]
    assert r["protocolVersion"] == "2025-11-25"


def test_unsupported_protocol_version(edge):
    out = edge.handle_line(json.dumps({"jsonrpc": "2.0", "id": 5, "method": "tools/list",
                                       "params": {"_meta": {m.META_VERSION: "2030-01-01", m.META_CLIENT_CAPS: {}}}}))
    e = json.loads(out)["error"]
    assert e["code"] == -32022 and e["data"]["supported"] == ["2026-07-28"] and e["data"]["requested"] == "2030-01-01"
    out = edge.handle_line(json.dumps({"jsonrpc": "2.0", "id": 5, "method": "tools/list",
                                       "params": {"_meta": {m.META_VERSION: m.MODERN_VERSION}}}))
    assert json.loads(out)["error"]["code"] == m.INVALID_PARAMS


def test_batch_and_malformed(edge):
    assert json.loads(edge.handle_line("[]"))["error"]["code"] == m.INVALID_REQUEST
    assert json.loads(edge.handle_line('[{"jsonrpc":"2.0","id":1,"method":"ping"}]'))["error"]["code"] == m.INVALID_REQUEST
    assert json.loads(edge.handle_line("{not json"))["error"]["code"] == m.PARSE_ERROR
    assert json.loads(edge.handle_line('{"jsonrpc":"2.0","id":1,"method":"x","params":{"a":NaN}}'))["error"]["code"] == m.PARSE_ERROR
    assert json.loads(edge.handle_line(b"\xff\xfe"))["error"]["code"] == m.PARSE_ERROR
    assert json.loads(edge.handle_line('{"id":1}'))["error"]["code"] == m.INVALID_REQUEST
    assert edge.handle_line("   ") is None
    assert rpc(edge, "nope")["error"]["code"] == m.METHOD_NOT_FOUND
    assert rpc(edge, "tools/call", {"name": "../etc", "arguments": {}})["error"]["code"] == m.INVALID_PARAMS
    assert rpc(edge, "tools/call", {"name": "ask", "arguments": []})["error"]["code"] == m.INVALID_PARAMS


def test_rate_limit(db):
    t = [0.0]
    e = m.McpEdge(db, max_calls_per_minute=2, clock=lambda: t[0])
    try:
        assert not call(e, "get_unit", {"unit_id": ART2})["isError"]
        assert not call(e, "get_unit", {"unit_id": ART2})["isError"]
        assert call(e, "get_unit", {"unit_id": ART2})["structuredContent"]["error"]["kind"] == "RateLimited"
    finally:
        e.close()


def test_engine_failure_is_not_a_traceback(db):
    class Boom:
        def unit(self, *a, **k):
            raise RuntimeError("secret path /etc/x")

    e = m.McpEdge(db, engine=Boom())
    r = call(e, "get_unit", {"unit_id": ART2})
    assert r["isError"] and r["structuredContent"]["error"]["kind"] == "EngineError"
    assert "secret" not in r["content"][0]["text"] and "Traceback" not in r["content"][0]["text"]


def test_serve_writes_only_protocol_lines(edge):
    lines = [
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": META}}),
        "garbage",
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"_meta": META, "name": "ask", "arguments": {"question": "texto sintético"}}}),
    ]
    out = io.BytesIO()
    edge.serve(io.BytesIO(("\n".join(lines) + "\n").encode()), out)
    rows = out.getvalue().decode().splitlines()
    assert len(rows) == 3
    for row in rows:
        assert json.loads(row)["jsonrpc"] == "2.0"


def test_subprocess_stdout_is_protocol_only(db):
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": META}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"_meta": META, "name": "ask", "arguments": {"question": "Qual o texto do art. 2º?", "as_of": "2021-01-01"}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"_meta": META, "name": "search", "arguments": {"question": "x", "k": 0}}},
    ]
    stdin = "\n".join(json.dumps(x) for x in msgs) + "\nnot json\n"
    src = str(Path(m.__file__).resolve().parent.parent)
    proc = subprocess.run([sys.executable, "-m", "heuresis.mcp_edge", "--db", db], input=stdin, capture_output=True,
                          text=True, timeout=60, env={"PYTHONPATH": src, "PATH": "/usr/bin:/bin"})
    assert proc.returncode == 0, proc.stderr
    rows = [json.loads(x) for x in proc.stdout.splitlines()]
    assert len(rows) == 4 and all(r["jsonrpc"] == "2.0" for r in rows)
    assert rows[1]["result"]["structuredContent"]["status"] == "answered"
    assert rows[2]["result"]["isError"] is True
    assert rows[3]["error"]["code"] == m.PARSE_ERROR
    assert "Traceback" not in proc.stderr
