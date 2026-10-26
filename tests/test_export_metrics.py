"""export_metrics: formato Prometheus y envio a la Pushgateway (servidor local que captura la peticion)."""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import export_metrics as em


@pytest.fixture
def gateway():
    captured = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            captured.update(path=self.path, body=self.rfile.read(n).decode(), type=self.headers.get("Content-Type"))
            self.send_response(200); self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True).start()
    captured["url"] = f"http://127.0.0.1:{server.server_port}"
    yield captured
    server.shutdown()


def _env(monkeypatch, gateway, **kv):
    for var in ("SCORE_GRADE", "SCORE_PENALTY", "VULN_CRITICAL", "VULN_HIGH", "VULN_MEDIUM", "VULN_LOW", "DORA_ENV"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("PUSHGATEWAY_URL", gateway["url"])
    monkeypatch.setenv("CI_PROJECT_NAME", "mi-app")
    monkeypatch.setenv("CI_COMMIT_SHA", "abc123")
    for k, v in kv.items():
        monkeypatch.setenv(k, v)


def test_envia_las_metricas_en_formato_prometheus(gateway, monkeypatch):
    _env(monkeypatch, gateway, SCORE_GRADE="B", SCORE_PENALTY="12.5", VULN_CRITICAL="1", VULN_HIGH="2",
         VULN_MEDIUM="3", VULN_LOW="4", DORA_ENV="staging")
    em.main()
    assert gateway["path"] == "/metrics/job/github-actions/service/mi-app"
    assert gateway["type"] == "text/plain; version=0.0.4"
    body = gateway["body"]
    assert 'github_security_health_percent{service="mi-app",env="staging",commit="abc123"} 85' in body
    assert 'github_security_penalty_points{service="mi-app",env="staging"} 12.5' in body
    for sev, n in (("critical", 1), ("high", 2), ("medium", 3), ("low", 4)):
        assert f'github_security_vulnerabilities_total{{service="mi-app",severity="{sev}"}} {n}' in body
    assert body.endswith("\n")


@pytest.mark.parametrize("grado,esperado", [("A+", 100), ("A", 95), ("B", 85), ("C", 70), ("D", 50), ("F", 20)])
def test_mapa_de_notas_a_porcentaje(gateway, monkeypatch, grado, esperado):
    _env(monkeypatch, gateway, SCORE_GRADE=grado)
    em.main()
    assert f'commit="abc123"}} {esperado}' in gateway["body"]


def test_valores_por_defecto(gateway, monkeypatch):
    _env(monkeypatch, gateway)
    em.main()
    assert 'env="production"' in gateway["body"] and 'severity="critical"} 0' in gateway["body"]


def test_pushgateway_inalcanzable_avisa_sin_romper(monkeypatch, capsys):
    monkeypatch.setenv("PUSHGATEWAY_URL", "http://127.0.0.1:1")
    em.main()
    assert "No se pudo conectar con la Pushgateway" in capsys.readouterr().err


def test_un_numero_invalido_en_las_vulnerabilidades_falla_en_voz_alta(gateway, monkeypatch):
    _env(monkeypatch, gateway, VULN_HIGH="muchas")
    with pytest.raises(ValueError):
        em.main()


def test_usa_variables_de_github_actions_si_no_hay_ci_project(gateway, monkeypatch):
    _env(monkeypatch, gateway)
    monkeypatch.delenv("CI_PROJECT_NAME")
    monkeypatch.delenv("CI_COMMIT_SHA")
    monkeypatch.setenv("GITHUB_REPOSITORY", "grs89/mi-repo")
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")
    em.main()
    assert gateway["path"] == "/metrics/job/github-actions/service/mi-repo"
    assert 'service="mi-repo",env="production",commit="deadbeef"' in gateway["body"]


def test_prefijo_de_metricas_configurable(gateway, monkeypatch):
    _env(monkeypatch, gateway, METRICS_PREFIX="ci")
    em.main()
    assert "ci_security_health_percent{" in gateway["body"]
    assert "github_security" not in gateway["body"]
