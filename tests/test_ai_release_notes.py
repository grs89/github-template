"""ai_release_notes: herramientas del agente contra repositorios git temporales."""
import subprocess

import pytest

pytest.importorskip("strands")
import ai_release_notes as rn  # noqa: E402


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "PATH": __import__("os").environ["PATH"], "HOME": str(cwd)})


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CI_PROJECT_DIR", str(tmp_path))
    _git(tmp_path, "init", "-q", "-b", "main")
    for i, tag in ((1, "v1"), (2, "v2")):
        (tmp_path / f"f{i}.txt").write_text(str(i))
        _git(tmp_path, "add", "."); _git(tmp_path, "commit", "-qm", f"feat: cambio {i}\n\ncuerpo {i}")
        _git(tmp_path, "tag", tag)
    return tmp_path


def test_get_previous_tag(repo):
    assert rn.get_previous_tag("v2") == {"found": True, "previous_tag": "v1"}
    assert rn.get_previous_tag("v1")["found"] is False
    assert rn.get_previous_tag("no-existe")["found"] is False


def test_tag_vacio_no_tiene_anterior(repo):
    assert rn.get_previous_tag("")["found"] is False


@pytest.mark.parametrize("ref", ["--output=pwn", "-x", "a b", "a;b"])
def test_referencias_git_invalidas_se_rechazan(repo, ref):
    assert rn.get_previous_tag(ref)["found"] is False
    r = rn.get_commit_log(ref, "v2")
    assert r["count"] == 0 and r["error"] == "referencia git no valida"
    assert not (repo / "pwn").exists()


def test_get_commit_log_rango_y_mensajes_completos(repo):
    r = rn.get_commit_log("v1", "v2")
    assert r["count"] == 1 and "feat: cambio 2" in r["commits"]
    full = rn.get_commit_log("v1", "v2", full_messages=True)
    assert "cuerpo 2" in full["commits"] and "--- COMMIT ---" in full["commits"]


def test_get_commit_log_sin_origen_toma_los_ultimos_50(repo):
    r = rn.get_commit_log("", "HEAD")
    assert r["count"] == 2


def test_read_changelog(repo):
    assert rn.read_changelog() == {"found": False, "content": ""}
    (repo / "CHANGELOG.md").write_text("# Cambios\n## [2.0.0]\n- nuevo\n## [1.0.0]\n- viejo\n")
    assert "viejo" in rn.read_changelog()["content"]
    seccion = rn.read_changelog("v2.0.0")["content"]
    assert "nuevo" in seccion and "viejo" not in seccion
    assert "viejo" in rn.read_changelog("v9.9.9")["content"]   # sin la seccion: primeras lineas


def test_save_release_notes_dentro_del_repo(repo):
    r = rn.save_release_notes("# Notas\n- a\n")
    assert r["status"] == "saved" and (repo / "RELEASE_NOTES.md").read_text() == "# Notas\n- a\n"
    assert rn.save_release_notes("x", "docs/notas.md")["status"] == "error"   # el directorio no existe: no se crea
    (repo / "docs").mkdir()
    assert rn.save_release_notes("x", "docs/notas.md")["status"] == "saved"


@pytest.mark.parametrize("destino", ["../fuera.md", "ABSOLUTA", ".git/config", ".gitlab-ci.yml", "Dockerfile", "x.tf"])
def test_save_release_notes_rechaza_rutas_peligrosas(repo, destino):
    absoluta = repo.parent / "absoluta-fuera.md"      # fuera del repo, dentro del tmp del test
    destino = str(absoluta) if destino == "ABSOLUTA" else destino
    assert rn.save_release_notes("PWNED", destino)["status"] == "error"
    assert not (repo.parent / "fuera.md").exists() and not absoluta.exists()


def test_turn_limiter_cancela_tras_el_maximo():
    from types import SimpleNamespace
    hook = rn._turn_limiter(1)
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
            callback_handler(current_tool_use={"name": "save_release_notes"})
        return "hecho"


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CI_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CI_COMMIT_TAG", "v9.9")
    for var in ("RELEASE_NOTES_OUTPUT", "AI_MAX_TURNS", "CI_COMMIT_BEFORE_SHA"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(rn, "_build_model", lambda: object())
    monkeypatch.setattr(rn, "Agent", _AgenteFalso)
    _AgenteFalso.fallar = False
    return tmp_path


def test_main_ejecuta_el_agente_con_el_tag_y_limita_los_turnos(entorno, capsys):
    (entorno / "RELEASE_NOTES.md").write_text("# Notas\n")
    rn.main()
    agente = _AgenteFalso.ultimo
    assert "v9.9" in agente.prompt and len(agente.hooks) == 1
    salida = capsys.readouterr().out
    assert "Agente finalizado" in salida and "save_release_notes" in salida and "Vista previa" in salida


def test_main_si_el_modelo_no_se_puede_construir_termina_con_error(entorno, monkeypatch):
    def _falla():
        raise RuntimeError("sin credenciales")
    monkeypatch.setattr(rn, "_build_model", _falla)
    with pytest.raises(SystemExit) as e:
        rn.main()
    assert e.value.code == 1


def test_main_si_el_agente_falla_deja_un_archivo_minimo_y_sale_con_error(entorno):
    _AgenteFalso.fallar = True
    with pytest.raises(SystemExit) as e:
        rn.main()
    assert e.value.code == 1
    assert "Notas no disponibles" in (entorno / "RELEASE_NOTES.md").read_text()
