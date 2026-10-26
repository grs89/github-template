"""ai_remediation: hallazgos SARIF / gl-sast -> comentarios `suggestion` en el Pull Request de GitHub."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import ai_remediation as ar

SARIF = {
    "runs": [{
        "tool": {"driver": {"rules": [{"id": "R1", "shortDescription": {"text": "Hardcoded secret"}}]}},
        "results": [
            {"ruleId": "R1", "level": "error", "message": {"text": "secret en código"},
             "locations": [{"physicalLocation": {"artifactLocation": {"uri": "file://app.py"}, "region": {"startLine": 2}}}]},
            {"ruleId": "R1", "message": {"text": "sin ubicación"}},
        ],
    }]
}
GL_SAST = {"vulnerabilities": [{"id": "x", "message": "m", "description": "d", "severity": "High",
                                 "location": {"file": "a.py", "start_line": 7}}]}


@pytest.fixture
def github():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
            code = 422 if body["path"] == "bad.py" else 201
            self.send_response(code); self.end_headers(); self.wfile.write(b"{}")

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True).start()
    yield {"url": f"http://127.0.0.1:{server.server_port}", "calls": calls}
    server.shutdown()


def test_load_findings_sarif_normaliza_y_descarta_hallazgos_sin_ubicacion():
    f = ar.load_findings(SARIF)
    assert f == [{"id": "R1", "file": "app.py", "line": 2, "message": "secret en código",
                  "description": "Hardcoded secret", "severity": "High"}]


def test_load_findings_gitlab_sast():
    f = ar.load_findings(GL_SAST)
    assert f[0]["file"] == "a.py" and f[0]["line"] == 7 and f[0]["severity"] == "High"


def test_prompt_pide_bloque_suggestion_de_github_y_marca_el_contexto_como_no_confiable():
    p = ar.build_prompt(ar.load_findings(GL_SAST)[0], "x = 1", "ctx")
    assert "```suggestion\n" in p and "suggestion:-0+0" not in p
    assert "untrusted" in p


def test_post_envia_comentario_de_revision_autenticado(github):
    payload = {"body": "b", "commit_id": "sha", "path": "app.py", "line": 2, "side": "RIGHT"}
    assert ar.post_github_review_comment("o/r", "5", "tok", payload, api_url=github["url"]) is True
    c = github["calls"][0]
    assert c["path"] == "/repos/o/r/pulls/5/comments" and c["auth"] == "Bearer tok" and c["body"] == payload


def test_post_devuelve_false_si_github_rechaza_la_linea(github):
    assert ar.post_github_review_comment("o/r", "5", "t", {"path": "bad.py"}, api_url=github["url"]) is False


def test_contexto_de_vulnerabilidad(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("\n".join(f"l{i}" for i in range(1, 21)))
    line, ctx = ar.get_vulnerability_context(str(f), 10, 2)
    assert line == "l10" and ctx.splitlines() == ["l8", "l9", "l10", "l11", "l12"]
    assert ar.get_vulnerability_context(str(f), 99) == (None, "")
    assert ar.get_vulnerability_context(str(tmp_path / "no.py"), 1) == (None, "")


def _env(monkeypatch, github, **kv):
    for k in ("PR_NUMBER", "GH_TOKEN", "GITHUB_TOKEN", "PR_HEAD_SHA", "GITHUB_SHA", "AI_MAX_SUGGESTIONS"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_API_URL", github["url"])
    for k, v in kv.items():
        monkeypatch.setenv(k, v)


def test_main_se_omite_fuera_de_un_pull_request(github, monkeypatch, capsys):
    _env(monkeypatch, github)
    with pytest.raises(SystemExit) as e:
        ar.main()
    assert e.value.code == 0 and "Omitiendo" in capsys.readouterr().out
    assert github["calls"] == []


def test_main_publica_sugerencias_hasta_el_limite(github, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("a = 1\nsecret = 'x'\nb = 2\n")
    (tmp_path / "r.sarif").write_text(json.dumps(SARIF))
    _env(monkeypatch, github, PR_NUMBER="9", GH_TOKEN="tok", PR_HEAD_SHA="abc", AI_PROVIDER="ollama")
    monkeypatch.setattr(ar, "query_llm", lambda *a, **k: "```suggestion\nsecret = os.environ['S']\n```")
    ar.main()
    assert len(github["calls"]) == 1
    body = github["calls"][0]["body"]
    assert body["path"] == "app.py" and body["line"] == 2 and body["commit_id"] == "abc" and body["side"] == "RIGHT"
    assert "```suggestion" in body["body"]


def test_main_descarta_respuestas_sin_bloque_suggestion(github, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("a\nb\nc\n")
    (tmp_path / "r.sarif").write_text(json.dumps(SARIF))
    _env(monkeypatch, github, PR_NUMBER="9", GH_TOKEN="tok", PR_HEAD_SHA="abc")
    monkeypatch.setattr(ar, "query_llm", lambda *a, **k: "no sé")
    ar.main()
    assert github["calls"] == []


def test_main_respeta_ai_max_suggestions(github, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("a\nb\nc\n")
    two = json.loads(json.dumps(SARIF))
    two["runs"][0]["results"].insert(0, two["runs"][0]["results"][0])
    (tmp_path / "r.sarif").write_text(json.dumps(two))
    _env(monkeypatch, github, PR_NUMBER="9", GH_TOKEN="tok", PR_HEAD_SHA="abc", AI_MAX_SUGGESTIONS="1")
    monkeypatch.setattr(ar, "query_llm", lambda *a, **k: "```suggestion\nx\n```")
    ar.main()
    assert len(github["calls"]) == 1
