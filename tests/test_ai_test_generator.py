"""ai_test_generator: herramientas del agente confinadas al repositorio."""
import os
import subprocess

import pytest

pytest.importorskip("strands")
import ai_test_generator as tg  # noqa: E402


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "PATH": os.environ["PATH"], "HOME": str(cwd)})


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CI_PROJECT_DIR", str(tmp_path))
    return tmp_path


def _con_historial(repo):
    _git(repo, "init", "-q", "-b", "main")
    (repo / "api").mkdir()
    (repo / "api" / "a.py").write_text("x = 1\n"); (repo / "otro.txt").write_text("o\n")
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "base")
    (repo / "api" / "a.py").write_text("x = 2\n"); (repo / "otro.txt").write_text("p\n")
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "cambio")


def test_get_code_diff_sin_origen_usa_head_anterior_y_filtra_por_servicio(repo):
    _con_historial(repo)
    r = tg.get_code_diff("api")
    assert r["has_changes"] and r["base_ref"] == "HEAD~1" and "api/a.py" in r["diff"] and "otro.txt" not in r["diff"]
    assert "otro.txt" in tg.get_code_diff(".")["diff"]


def test_get_code_diff_sin_cambios(repo):
    _con_historial(repo)
    (repo / "otro.txt").write_text("solo otro archivo\n")
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "fuera del servicio")
    assert tg.get_code_diff("api")["has_changes"] is False


def test_read_source_files_excluye_tests_y_respeta_el_maximo(repo):
    (repo / "svc").mkdir()
    for nombre in ("a.py", "b.py", "c.py", "d.py", "test_a.py"):
        (repo / "svc" / nombre).write_text(f"# {nombre}\n")
    r = tg.read_source_files("svc", "python", max_files=2)
    assert r["count"] == 2 and not any("test_" in f for f in r["files"])


@pytest.mark.parametrize("ruta", ["..", "../otro", "/etc", "/tmp"])
def test_read_source_files_rechaza_rutas_fuera_del_repo(repo, ruta):
    r = tg.read_source_files(ruta, "python")
    assert r["count"] == 0 and "fuera del repositorio" in r["error"]


def test_detect_test_framework(repo):
    (repo / "pytest.ini").write_text("[pytest]\n")
    assert tg.detect_test_framework(".", "python")["framework"] == "pytest"
    (repo / "web").mkdir(); (repo / "web" / "package.json").write_text('{"devDependencies": {"jest": "^29"}}')
    assert tg.detect_test_framework("web", "js")["framework"] == "jest"
    assert tg.detect_test_framework(".", "go")["framework"] == "unknown"


def test_detect_test_framework_rechaza_rutas_fuera_del_repo(repo):
    assert "fuera del repositorio" in tg.detect_test_framework("../..", "python")["error"]


def test_save_test_file_escribe_y_limpia_las_vallas_markdown(repo):
    r = tg.save_test_file("```python\ndef test_x():\n    assert True\n```", ".", "python")
    assert r["status"] == "saved"
    assert (repo / "generated-tests" / "test_ai_generated.py").read_text() == "def test_x():\n    assert True"


def test_save_test_file_en_el_subdirectorio_del_servicio(repo):
    (repo / "svc").mkdir()
    r = tg.save_test_file("x", "svc", "go")
    assert r["status"] == "saved" and (repo / "svc" / "generated-tests" / "ai_generated_test.go").exists()


@pytest.mark.parametrize("out_dir,service", [("../fuera", "."), ("ABSOLUTA", "."), (".git/hooks", "."), (".", "../otro")])
def test_save_test_file_rechaza_rutas_peligrosas(repo, out_dir, service):
    absoluta = repo.parent / "tests-fuera"            # fuera del repo, dentro del tmp del test
    out_dir = str(absoluta) if out_dir == "ABSOLUTA" else out_dir
    r = tg.save_test_file("PWNED", service, "python", out_dir=out_dir)
    assert r["status"] == "error"
    assert not absoluta.exists() and not (repo.parent / "fuera").exists()


def test_generate_scaffold(repo):
    assert "pytest" in tg.generate_scaffold("python")["scaffold"]
    assert "placeholder" in tg.generate_scaffold("cobol")["scaffold"]


def test_turn_limiter_cancela_tras_el_maximo():
    from types import SimpleNamespace
    hook = tg._turn_limiter(1)
    a, b = SimpleNamespace(cancel=False), SimpleNamespace(cancel=False)
    hook(a); hook(b)
    assert not a.cancel and b.cancel


# ─────────────── main(): flujo con un agente falso ───────────────

class _AgenteFalso:
    ultimo = None
    fallar = False

    def __init__(self, **kw):
        self.kw, self.hooks, self.prompt = kw, [], None
        _AgenteFalso.ultimo = self

    def add_hook(self, callback, event_type=None):
        self.hooks.append((callback, event_type))

    def __call__(self, prompt, callback_handler=None):
        self.prompt = prompt
        if _AgenteFalso.fallar:
            raise RuntimeError("modelo caido")
        if callback_handler:
            callback_handler(data="texto ")
            callback_handler(current_tool_use={"name": "save_test_file"})
        return "hecho"


@pytest.fixture
def entorno(repo, monkeypatch):
    monkeypatch.setenv("SERVICE_PATH", ".")
    monkeypatch.setenv("SERVICE_LANG", "python")
    monkeypatch.delenv("AI_MAX_TURNS", raising=False)
    monkeypatch.setattr(tg, "_build_model", lambda: object())
    monkeypatch.setattr(tg, "Agent", _AgenteFalso)
    _AgenteFalso.fallar = False
    return repo


def test_main_pasa_servicio_y_lenguaje_al_agente_y_lista_lo_generado(entorno, capsys):
    (entorno / "generated-tests").mkdir()
    (entorno / "generated-tests" / "test_ai_generated.py").write_text("x")
    tg.main()
    agente = _AgenteFalso.ultimo
    assert "python" in agente.prompt and "Ruta del servicio: ." in agente.prompt and len(agente.hooks) == 1
    salida = capsys.readouterr().out
    assert "Agente finalizado" in salida and "test_ai_generated.py" in salida and "save_test_file" in salida


def test_main_sin_archivos_generados_lo_indica(entorno, capsys):
    tg.main()
    assert "No se generaron archivos nuevos" in capsys.readouterr().out


def test_main_si_el_modelo_no_se_puede_construir_termina_con_error(entorno, monkeypatch):
    def _falla():
        raise RuntimeError("sin credenciales")
    monkeypatch.setattr(tg, "_build_model", _falla)
    with pytest.raises(SystemExit) as e:
        tg.main()
    assert e.value.code == 1


def test_main_si_el_agente_falla_sale_con_error(entorno):
    _AgenteFalso.fallar = True
    with pytest.raises(SystemExit) as e:
        tg.main()
    assert e.value.code == 1
