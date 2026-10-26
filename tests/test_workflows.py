"""Validación estática de los workflows reutilizables (.github/workflows/*.yml).

Equivalente a validate_templates.py de las plantillas GitLab: garantiza que cada plantilla es YAML válido,
declara todo lo que usa y no arrastra restos de GitLab. La validación semántica profunda la hace actionlint
(workflow quality-lint_templates.yml).
"""
import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).resolve().parent.parent / ".github" / "workflows").glob("*.yml"))
SELF_REF = "grs89/github-template"
PINNED_REF = re.compile(r"^(v?\d[\w.]*|[0-9a-f]{40})$")
GITLAB_LEFTOVERS = [r"\$\{?CI_[A-Z_]+", r"JOB-TOKEN", r"registry\.gitlab\.com", r"/api/v4", r"\.gitlab-ci\.yml",
                    r"CI_JOB_TOKEN", r"gitlab-ci-token"]


def _load(path):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    triggers = doc.get("on", doc.get(True))  # PyYAML parsea `on` como True
    return doc, triggers if isinstance(triggers, dict) else {t: None for t in (triggers if isinstance(triggers, list) else [triggers])}


def _ids(paths):
    return [p.name for p in paths]


@pytest.fixture(scope="module", params=WORKFLOWS, ids=_ids(WORKFLOWS))
def wf(request):
    doc, triggers = _load(request.param)
    return request.param, request.param.read_text(encoding="utf-8"), doc, triggers


def _jobs(doc):
    return doc["jobs"].items()


def test_hay_workflows():
    assert len(WORKFLOWS) > 60


def test_estructura_basica(wf):
    path, _, doc, triggers = wf
    assert doc.get("name"), f"{path.name}: falta name"
    assert triggers, f"{path.name}: falta on"
    for jid, job in _jobs(doc):
        assert "runs-on" in job or "uses" in job, f"{path.name}:{jid} sin runs-on/uses"
        assert not ("runs-on" in job and "uses" in job)


def test_needs_apuntan_a_jobs_existentes(wf):
    path, _, doc, _ = wf
    for jid, job in _jobs(doc):
        needs = job.get("needs") or []
        for n in [needs] if isinstance(needs, str) else needs:
            assert n in doc["jobs"], f"{path.name}:{jid} needs inexistente '{n}'"


def test_sin_restos_de_gitlab(wf):
    path, text, _, _ = wf
    for pat in GITLAB_LEFTOVERS:
        assert not re.search(pat, text), f"{path.name}: resto de GitLab /{pat}/"


def test_inputs_usados_estan_declarados(wf):
    path, text, doc, triggers = wf
    if "workflow_call" not in triggers:
        pytest.skip("no es reutilizable")
    wc = triggers["workflow_call"] or {}
    declared = set((wc.get("inputs") or {}))
    used = set(re.findall(r"\$\{\{[^}]*?\binputs\.([A-Za-z0-9_-]+)", text))
    assert used <= declared, f"{path.name}: inputs sin declarar {sorted(used - declared)}"


def test_secrets_usados_estan_declarados(wf):
    path, text, doc, triggers = wf
    if "workflow_call" not in triggers:
        pytest.skip("no es reutilizable")
    wc = triggers["workflow_call"] or {}
    declared = set((wc.get("secrets") or {})) | {"GITHUB_TOKEN"}
    used = set(re.findall(r"\$\{\{[^}]*?\bsecrets\.([A-Za-z0-9_]+)", text))
    # los workflows que además se disparan solos (push/tags) pueden usar secrets del repo directamente
    if set(triggers) - {"workflow_call"}:
        pytest.skip("workflow con triggers propios")
    assert used <= declared, f"{path.name}: secrets sin declarar {sorted(used - declared)}"


def test_defaults_coinciden_con_el_tipo(wf):
    path, _, _, triggers = wf
    for trig in ("workflow_call", "workflow_dispatch"):
        for name, spec in ((triggers.get(trig) or {}).get("inputs") or {}).items():
            typ, default = spec.get("type"), spec.get("default")
            if default is None:
                continue
            ok = {"boolean": isinstance(default, bool), "string": isinstance(default, str),
                  "number": isinstance(default, (int, float)) and not isinstance(default, bool),
                  "choice": True, "environment": True}.get(typ, True)
            assert ok, f"{path.name}: input {name} type={typ} default={default!r}"


def test_acciones_externas_con_version_fija(wf):
    path, text, _, _ = wf
    for ref in re.findall(r"uses:\s*([\w.-]+/[\w./-]+@[\w.-]+)", text):
        action, version = ref.rsplit("@", 1)
        if action.startswith(SELF_REF):
            continue
        assert PINNED_REF.match(version), f"{path.name}: {ref} usa una referencia móvil"


def test_permisos_declarados(wf):
    path, _, doc, _ = wf
    for jid, job in _jobs(doc):
        if "uses" in job and "runs-on" not in job:
            continue
        assert "permissions" in doc or "permissions" in job, f"{path.name}:{jid} sin permissions (mínimo privilegio)"


def test_pasos_run_no_interpolan_entradas_no_confiables(wf):
    """Inyección de comandos: inputs/secrets/ref/outputs/github.event deben pasar por env, no por ${{ }} dentro de run."""
    path, _, doc, _ = wf
    bad = re.compile(r"\$\{\{\s*(inputs\.|secrets\.|github\.ref|github\.head_ref|github\.event\.(pull_request\.(title|body|head\.ref)|head_commit\.message|issue\.title|comment\.body)|(needs|steps)\.[\w-]+\.outputs\.)")
    for jid, job in _jobs(doc):
        for step in job.get("steps") or []:
            m = bad.search(step.get("run") or "")
            assert not m, f"{path.name}:{jid} interpola {m.group(0)} dentro de run"


def test_los_inputs_de_script_no_se_usan_para_el_shell_sin_env():
    """Los workflows nuevos/portados no deben tener run con ${{ secrets.* }} (se pasan por env)."""
    for path in WORKFLOWS:
        doc, _ = _load(path)
        for jid, job in _jobs(doc):
            for step in job.get("steps") or []:
                assert "${{ secrets." not in (step.get("run") or ""), f"{path.name}:{jid} secret dentro de run"
