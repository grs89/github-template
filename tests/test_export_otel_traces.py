"""export_otel_traces: run de GitHub Actions -> payload OTLP y envío al colector."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import export_otel_traces as ot

RUN = {"id": 42, "name": "CI", "run_number": 7, "head_branch": "main", "head_sha": "abc",
       "html_url": "https://github.com/o/r/actions/runs/42", "conclusion": "success",
       "run_started_at": "2026-01-01T10:00:00Z", "updated_at": "2026-01-01T10:05:00Z"}
JOBS = [
    {"id": 1, "name": "Test & Lint [backend] / lint", "conclusion": "success",
     "started_at": "2026-01-01T10:00:10Z", "completed_at": "2026-01-01T10:02:00Z", "runner_name": "gh-1",
     "steps": [{"number": 1, "name": "Checkout", "conclusion": "success",
                "started_at": "2026-01-01T10:00:10Z", "completed_at": "2026-01-01T10:00:20Z"}]},
    {"id": 2, "name": "build", "conclusion": "failure",
     "started_at": "2026-01-01T10:02:00Z", "completed_at": "2026-01-01T10:04:00Z", "steps": []},
]


@pytest.fixture
def collector():
    got = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_POST(self):
            got["path"] = self.path
            got["auth"] = self.headers.get("Authorization")
            got["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200); self.end_headers()

    s = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=lambda: s.serve_forever(poll_interval=0.01), daemon=True).start()
    got["url"] = f"http://127.0.0.1:{s.server_port}"
    yield got
    s.shutdown()


def test_ids_deterministas_con_longitud_otlp():
    t = ot.generate_trace_id(42, "repo")
    assert t == ot.generate_trace_id(42, "repo") and len(t) == 32
    assert len(ot.generate_span_id("job-1")) == 16


def test_iso_to_nanos_y_fallback():
    assert ot.iso_to_nanos("1970-01-01T00:00:01Z") == 1_000_000_000
    assert ot.iso_to_nanos(None, 5) == 5 and ot.iso_to_nanos("basura", 7) == 7


@pytest.mark.parametrize("name,expected", [("Test & Lint [backend] / lint", "backend"), ("build", "repo"), ("", "repo")])
def test_servicio_a_partir_del_nombre_del_job(name, expected):
    assert ot.extract_service_name(name, "repo") == expected


@pytest.mark.parametrize("c,s", [("success", "success"), ("failure", "failed"), ("cancelled", "failed"), (None, "unknown")])
def test_conclusion_a_estado(c, s):
    assert ot.conclusion_to_status(c) == s


def test_payload_agrupa_por_servicio_y_encadena_padres():
    payload, trace_id = ot.build_trace_payload(RUN, JOBS, "repo", now_ns=0)
    names = {rs["resource"]["attributes"][0]["value"]["stringValue"]: rs["scopeSpans"][0]["spans"] for rs in payload["resourceSpans"]}
    assert set(names) == {"repo", "repo:backend"}
    root = names["repo"][0]
    assert "parentSpanId" not in root and root["traceId"] == trace_id
    assert root["status"]["code"] == 1
    build = next(s for s in names["repo"] if s["name"] == "build")
    assert build["parentSpanId"] == root["spanId"] and build["status"]["code"] == 2
    backend = names["repo:backend"]
    job_span, step_span = backend[0], backend[1]
    assert job_span["parentSpanId"] == root["spanId"] and step_span["parentSpanId"] == job_span["spanId"]


def test_spans_siempre_terminan_despues_de_empezar():
    payload, _ = ot.build_trace_payload(RUN, JOBS, "repo", now_ns=0)
    for rs in payload["resourceSpans"]:
        for s in rs["scopeSpans"][0]["spans"]:
            assert int(s["endTimeUnixNano"]) > int(s["startTimeUnixNano"])


def test_envio_otlp_agrega_v1_traces_y_bearer(collector):
    assert ot.send_otlp_payload(collector["url"], {"resourceSpans": []}, "tok") is True
    assert collector["path"] == "/v1/traces" and collector["auth"] == "Bearer tok"


def test_envio_a_colector_caido_no_lanza():
    assert ot.send_otlp_payload("http://127.0.0.1:1", {"resourceSpans": []}) is False


def test_main_sin_colector_no_hace_nada(monkeypatch, capsys):
    monkeypatch.delenv("OTEL_COLLECTOR_URL", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    ot.main()
    assert "Omitiendo" in capsys.readouterr().out


def test_export_completo_contra_api_y_colector_simulados(collector, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/repo")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv("GH_TOKEN", "t")
    monkeypatch.delenv("GRAFANA_URL", raising=False)

    def fake_get(url, token=None):
        return RUN if url.endswith("/runs/42") else {"jobs": JOBS}
    monkeypatch.setattr(ot, "github_api_get", fake_get)
    assert ot.export_full_run_trace(collector["url"]) is True
    spans = sum(len(rs["scopeSpans"][0]["spans"]) for rs in collector["body"]["resourceSpans"])
    assert spans == 4  # root + 2 jobs + 1 step


def test_export_se_omite_si_la_api_no_responde(collector, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/repo")
    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    monkeypatch.setattr(ot, "github_api_get", lambda *a, **k: None)
    assert ot.export_full_run_trace(collector["url"]) is False
    assert "body" not in collector
