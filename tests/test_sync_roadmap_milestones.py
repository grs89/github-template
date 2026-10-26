"""parse_roadmap: formatos soportados y fallback genérico por nombre de columna."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import sync_roadmap_milestones as sr


def _parse(tmp_path, text):
    f = tmp_path / "ROADMAP.md"
    f.write_text(text, encoding="utf-8")
    return sr.parse_roadmap(str(f))


def test_formato_estandar_no_cambia(tmp_path):
    r = _parse(tmp_path, "| 1 | **Entornos** | PaC | Alta | ✅ Completado |\n")
    assert [(i["number"], i["title"], i["priority"]) for i in r] == [("1", "Entornos", "Alta")]


def test_tabla_generica_sin_negrita_ni_numero(tmp_path):
    md = (
        "| Iniciativa | Prioridad | Estado | Fecha fin |\n"
        "|---|---|---|---|\n"
        "| Migrar a Helm | 🔴 Alta | En progreso | 2026-12-01 |\n"
        "| **Observabilidad** | Media | Done | |\n"
    )
    r = _parse(tmp_path, md)
    assert [i["title"] for i in r] == ["Migrar a Helm", "Observabilidad"]
    assert [i["number"] for i in r] == ["1", "2"]
    assert r[0]["priority"] == "Alta" and r[0]["due_date"] == "2026-12-01"
    assert "completado" in r[1]["status"].lower()


def test_tabla_generica_con_id_alfanumerico(tmp_path):
    md = "| ID | Nombre | Estado |\n|---|---|---|\n| A1 | Hardening | Pendiente |\n"
    r = _parse(tmp_path, md)
    assert r[0]["number"] == "A1" and r[0]["status"] == "Pendiente"


def test_sin_tabla_devuelve_vacio(tmp_path):
    assert _parse(tmp_path, "# Roadmap\n\nTexto sin tabla\n") == []


def test_fecha_inicio_y_fin_no_se_confunden(tmp_path):
    md = (
        "| Nombre | Etapa | Fecha Inicio | Fecha Fin |\n"
        "|---|---|---|---|\n"
        "| Hardening | Diseño | 2026-01-10 | 2026-03-20 |\n"
    )
    r = _parse(tmp_path, md)[0]
    assert r["start_date"] == "2026-01-10" and r["due_date"] == "2026-03-20"




# --- sincronización contra una API de GitHub falsa en local -------------------------------------

class FakeGitHub:
    def __init__(self):
        self.milestones, self.issues, self.requests = [], [], []


@pytest.fixture
def api():
    state = FakeGitHub()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n)) if n else {}

        def do_GET(self):
            state.requests.append(("GET", self.path, self.headers.get("Authorization")))
            if "/milestones" in self.path:
                self._send(200, state.milestones if "page=1" in self.path else [])
            elif "/issues" in self.path:
                self._send(200, state.issues if "page=1" in self.path else [])

        def do_POST(self):
            data = self._body(); state.requests.append(("POST", self.path, data))
            coll = state.milestones if self.path.endswith("/milestones") else state.issues
            item = {**data, "number": len(coll) + 1}
            coll.append(item); self._send(201, item)

        def do_PATCH(self):
            data = self._body(); state.requests.append(("PATCH", self.path, data))
            self._send(200, {**data, "number": int(self.path.rsplit("/", 1)[1])})

    server = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True).start()
    state.url = f"http://127.0.0.1:{server.server_port}"
    yield state
    server.shutdown()


def _item(number="1", title="Firma", status="⏳ Pendiente", priority="Alta"):
    return {"number": number, "title": title, "trend": "t", "priority": priority, "status": status,
            "description": "detalle", "start_date": "2026-01-01", "due_date": "2026-02-01", "release": "v1.0.0"}


def _by(api, method):
    return [(p, d) for m, p, d in api.requests if m == method]


def test_primera_sincronizacion_crea_milestone_e_issue_vinculado(api):
    sr.sync_to_github([_item()], "o/r", "tok", api_url=api.url)
    (ms_path, ms), = [x for x in _by(api, "POST") if x[0].endswith("/milestones")]
    (_, iss), = [x for x in _by(api, "POST") if x[0].endswith("/issues")]
    assert ms_path == "/repos/o/r/milestones" and ms["title"] == "#1: Firma" and ms["state"] == "open"
    assert ms["due_on"] == "2026-02-01T23:59:59Z"
    assert iss["title"] == "Iniciativa #1: Firma" and iss["milestone"] == 1
    assert "Prioridad: Alta" in iss["labels"] and "releases/tag/v1.0.0" in iss["body"]


def test_iniciativa_completada_se_crea_cerrada(api):
    sr.sync_to_github([_item(status="✅ Completado")], "o/r", "tok", api_url=api.url)
    assert all(d["state"] == "closed" for _, d in _by(api, "POST"))


def test_lo_existente_se_actualiza_en_vez_de_duplicarse(api):
    api.milestones.append({"title": "#1: Firma", "number": 5, "state": "open"})
    api.issues.append({"title": "Iniciativa #1: Firma", "number": 9})
    api.issues.append({"title": "Un PR", "number": 10, "pull_request": {}})
    sr.sync_to_github([_item(status="Completado")], "o/r", "tok", api_url=api.url)
    assert _by(api, "POST") == []
    paths = [p for p, _ in _by(api, "PATCH")]
    assert paths == ["/repos/o/r/milestones/5", "/repos/o/r/issues/9"]
    assert all(d["state"] == "closed" for _, d in _by(api, "PATCH"))
    assert _by(api, "PATCH")[1][1]["milestone"] == 5


def test_dry_run_no_toca_la_api(api):
    sr.sync_to_github([_item()], "o/r", "tok", dry_run=True, api_url=api.url)
    assert api.requests == []


def test_las_peticiones_llevan_bearer(api):
    sr.sync_to_github([_item()], "o/r", "tok", api_url=api.url)
    assert ("GET", "/repos/o/r/milestones?state=all&per_page=100&page=1", "Bearer tok") in api.requests


def test_error_de_red_devuelve_none_sin_romper():
    assert sr.make_github_request("http://127.0.0.1:1/x", "tok") is None


def test_main_sin_token_pasa_a_dry_run(api, tmp_path, monkeypatch):
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text("| 1 | **Firma** | t | Alta | Pendiente |\n")
    for var in ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(sr.sys, "argv", ["x", "--roadmap", str(roadmap), "--api-url", api.url])
    sr.main()
    assert api.requests == []


def test_main_con_token_y_repo_sincroniza(api, tmp_path, monkeypatch):
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text("| 1 | **Firma** | t | Alta | Pendiente |\n")
    monkeypatch.setattr(sr.sys, "argv", ["x", "--roadmap", str(roadmap), "--api-url", api.url, "--repo", "o/r", "--token", "tok"])
    sr.main()
    assert any(p.endswith("/milestones") for p, _ in _by(api, "POST"))


def test_release_por_defecto_usa_el_tag_de_github(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CI_COMMIT_TAG", raising=False)
    monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
    monkeypatch.setenv("GITHUB_REF_NAME", "v3.0.0")
    assert sr._get_default_release() == "v3.0.0"



def test_roadmap_inexistente_termina_con_error(tmp_path):
    with pytest.raises(SystemExit) as e:
        sr.parse_roadmap(str(tmp_path / "no-existe.md"))
    assert e.value.code == 1


def test_roadmap_sin_tabla_devuelve_lista_vacia(tmp_path):
    assert _parse(tmp_path, "solo texto\n") == []


def test_formato_extendido_de_8_columnas_lee_fechas_release_y_detalle(tmp_path):
    md = ("| 3 | **Firma** | Supply chain | 🔴 Alta | 2026-02-01 | 2026-03-15 | `v2.0.0` | ⏳ Pendiente |\n\n"
          "### 3. Firma\nDetalle de la firma.\n")
    (i,) = _parse(tmp_path, md)
    assert (i["start_date"], i["due_date"], i["release"], i["priority"]) == ("2026-02-01", "2026-03-15", "v2.0.0", "Alta")
    assert i["description"] == "Detalle de la firma."


def test_formato_deuda_tecnica_lee_id_y_detalle(tmp_path):
    md = ("| ID | Área | Qué |\n|---|---|---|\n| DT-01 | Tests | 🟠 Media |\n\n"
          "## DT-01 — Tests\nFaltan pruebas.\n")
    (i,) = _parse(tmp_path, md)
    assert i["number"] == "DT-01" and i["priority"] == "Media" and i["description"] == "Faltan pruebas."


def test_release_por_defecto_sale_de_la_variable_de_version_o_latest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CI_COMMIT_TAG", raising=False)
    monkeypatch.delenv("GITHUB_REF_TYPE", raising=False)
    (tmp_path / "version.yml").write_text('version: "v9.9.9"\n', encoding="utf-8")
    assert sr._get_default_release() == "v9.9.9"
    monkeypatch.setenv("CI_COMMIT_TAG", " v1.2.3 ")
    assert sr._get_default_release() == "v1.2.3"


def test_prioridad_y_fechas_se_normalizan():
    assert [sr._extract_priority(t) for t in ("🟠", "Low", "otra")] == ["Media", "Baja", "otra"]
    assert sr._clean_date("hasta 2026-05-06.") == "2026-05-06" and sr._clean_date("sin fecha") is None
